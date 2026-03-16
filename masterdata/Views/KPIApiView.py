"""
APIs pour les KPIs (Key Performance Indicators) du système AMS

Ce module implémente tous les KPIs définis dans KPI_ANALYSIS.md :
- KPIs basés sur la quantité (articles, items, emplacements, etc.)
- KPIs basés sur la valeur (achats, valeur résiduelle, amortissement)
- KPIs combinés et analyses temporelles
- Dashboard principal avec métriques critiques

ARCHITECTURE:
- Vue principale KPIDashboardAPIView : Tous les KPIs en une seule requête
- Vues spécialisées par catégorie : Quantité, Valeur, Temporels
- Cache Redis pour optimiser les performances
- Support des filtres par période et département
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, F, Q, Avg, Max, Min
from django.db.models.functions import TruncMonth, TruncYear, TruncQuarter
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class DateFilterHelper:
    """
    Classe utilitaire pour gérer les filtres par date avec tous les opérateurs
    """
    
    @staticmethod
    def parse_date_filter(date_str):
        """Parse une date depuis une chaîne de caractères"""
        if not date_str:
            return None
        
        # Essayer de parser comme date
        parsed_date = parse_date(date_str)
        if parsed_date:
            return parsed_date
        
        # Essayer de parser comme datetime
        parsed_datetime = parse_datetime(date_str)
        if parsed_datetime:
            return parsed_datetime.date()
        
        return None
    
    @staticmethod
    def build_date_filter(field_name, date_value, operator='exact'):
        """
        Construit un filtre Q pour un champ de date
        
        Args:
            field_name: Nom du champ de date (ex: 'date_achat')
            date_value: Valeur de date (peut être une chaîne ou un objet date)
            operator: Opérateur de comparaison ('exact', 'gte', 'lte', 'gt', 'lt', 'between')
        
        Returns:
            Q object pour le filtre
        """
        if not date_value:
            return Q()
        
        # Parser la date si c'est une chaîne
        if isinstance(date_value, str):
            parsed_date = DateFilterHelper.parse_date_filter(date_value)
            if not parsed_date:
                logger.warning(f"Impossible de parser la date: {date_value}")
                return Q()
            date_value = parsed_date
        
        # Construire le filtre selon l'opérateur
        if operator == 'exact':
            return Q(**{field_name: date_value})
        elif operator == 'gte':
            return Q(**{f"{field_name}__gte": date_value})
        elif operator == 'lte':
            return Q(**{f"{field_name}__lte": date_value})
        elif operator == 'gt':
            return Q(**{f"{field_name}__gt": date_value})
        elif operator == 'lt':
            return Q(**{f"{field_name}__lt": date_value})
        elif operator == 'between':
            # Pour 'between', date_value doit être une liste [date_debut, date_fin]
            if isinstance(date_value, list) and len(date_value) == 2:
                start_date = DateFilterHelper.parse_date_filter(date_value[0])
                end_date = DateFilterHelper.parse_date_filter(date_value[1])
                if start_date and end_date:
                    return Q(**{f"{field_name}__gte": start_date, f"{field_name}__lte": end_date})
            return Q()
        elif operator == 'year':
            return Q(**{f"{field_name}__year": date_value})
        elif operator == 'month':
            return Q(**{f"{field_name}__month": date_value})
        elif operator == 'day':
            return Q(**{f"{field_name}__day": date_value})
        else:
            logger.warning(f"Opérateur de date non reconnu: {operator}")
            return Q()
    
    @staticmethod
    def extract_date_filters_from_params(params):
        """
        Extrait tous les filtres de date des paramètres de requête
        
        Args:
            params: QueryDict des paramètres de requête
        
        Returns:
            dict: Dictionnaire des filtres de date organisés par champ
        """
        date_filters = {}
        
        # Champs de date disponibles
        date_fields = [
            'date_achat', 'date_reception', 'date_affectation', 'date_archive',
            'date_creation', 'date_debut', 'date_fin', 'created_at', 'updated_at'
        ]
        
        # Opérateurs supportés
        operators = ['exact', 'gte', 'lte', 'gt', 'lt', 'between', 'year', 'month', 'day']
        
        for field in date_fields:
            for operator in operators:
                param_name = f"{field}_{operator}"
                if param_name in params:
                    value = params[param_name]
                    
                    if operator == 'between':
                        # Pour 'between', on attend deux dates séparées par une virgule
                        if ',' in value:
                            dates = [d.strip() for d in value.split(',')]
                            if len(dates) == 2:
                                date_filters[param_name] = {
                                    'field': field,
                                    'operator': operator,
                                    'value': dates
                                }
                    else:
                        date_filters[param_name] = {
                            'field': field,
                            'operator': operator,
                            'value': value
                        }
        
        return date_filters
    
    @staticmethod
    def apply_date_filters_to_queryset(queryset, date_filters):
        """
        Applique les filtres de date à un queryset
        
        Args:
            queryset: Queryset Django
            date_filters: Dictionnaire des filtres de date
        
        Returns:
            Queryset filtré
        """
        for filter_name, filter_data in date_filters.items():
            field = filter_data['field']
            operator = filter_data['operator']
            value = filter_data['value']
            
            date_filter = DateFilterHelper.build_date_filter(field, value, operator)
            if date_filter:
                queryset = queryset.filter(date_filter)
        
        return queryset


from masterdata.models import (
    article, item, emplacement, zone, location, departement, 
    fournisseur, categorie, nature, marque, produit, inventaire,
    inventaire_emplacement, detail_inventaire, ArchiveItem,
    operation_article, TransferHistorique, tag, tagEmplacement,
    Personne
)


class KPIDashboardAPIView(APIView):
    """
    API principale pour le dashboard - Retourne tous les KPIs critiques
    
    GET /api/kpi/dashboard/
    
    Retourne :
    - KPIs de quantité (articles, items, emplacements)
    - KPIs de valeur (achats, valeur résiduelle)
    - KPIs de performance (taux d'affectation, inventaires)
    - Top 5 fournisseurs et départements
    """
    
    def get(self, request):
        try:
            # Extraire les filtres de date
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            # Construire la clé de cache avec les filtres
            cache_key = f'kpi_dashboard_main_{hash(str(sorted(date_filters.items())))}'
            
            # Vérifier le cache seulement si pas de filtres de date
            if not date_filters:
                cached_data = cache.get(cache_key)
                if cached_data:
                    return Response(cached_data, status=status.HTTP_200_OK)
            
            # Calculer tous les KPIs avec les filtres
            kpis = self._calculate_all_kpis(date_filters)
            
            # Mettre en cache pour 1 heure seulement si pas de filtres
            if not date_filters:
                cache.set(cache_key, kpis, 3600)
            
            return Response(kpis, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans KPIDashboardAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des KPIs: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_all_kpis(self, date_filters=None):
        """Calcule tous les KPIs principaux avec filtres de date"""
        
        # 1. KPIs BASÉS SUR LA QUANTITÉ
        quantity_kpis = self._calculate_quantity_kpis(date_filters)
        
        # 2. KPIs BASÉS SUR LA VALEUR
        value_kpis = self._calculate_value_kpis(date_filters)
        
        # 3. KPIs DE PERFORMANCE
        performance_kpis = self._calculate_performance_kpis(date_filters)
        
        # 4. TOP 5 FOURNISSEURS ET DÉPARTEMENTS
        top_entities = self._calculate_top_entities(date_filters)
        
        # 5. ÉTAT DES INVENTAIRES
        inventory_status = self._calculate_inventory_status(date_filters)
        
        return {
            'quantite': quantity_kpis,
            'valeur': value_kpis,
            'performance': performance_kpis,
            'top_entities': top_entities,
            'inventaires': inventory_status,
            'filtres_appliques': date_filters,
            'timestamp': timezone.now().isoformat()
        }
    
    def _calculate_quantity_kpis(self, date_filters=None):
        """Calcule les KPIs basés sur la quantité avec filtres de date"""
        
        # Appliquer les filtres de date aux articles
        articles_qs = article.objects.all()
        if date_filters:
            articles_qs = DateFilterHelper.apply_date_filters_to_queryset(articles_qs, date_filters)
        
        # Total Articles (quantité totale achetée)
        total_articles = articles_qs.aggregate(
            total=Sum('qte_recue', default=0)
        )['total'] or 0
        
        # Appliquer les filtres de date aux items
        items_qs = item.objects.filter(archive=False)
        if date_filters:
            items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
        
        # Total Items actifs
        total_items = items_qs.count()
        
        # Items affectés vs non affectés
        items_stats = items_qs.aggregate(
            total=Count('id'),
            affectes=Count('id', filter=Q(statut='affecter')),
            non_affectes=Count('id', filter=Q(statut='non affecter'))
        )
        
        # Items archivés (avec filtres de date sur date_archive)
        items_archives_qs = item.objects.filter(archive=True)
        if date_filters:
            items_archives_qs = DateFilterHelper.apply_date_filters_to_queryset(items_archives_qs, date_filters)
        items_archives = items_archives_qs.count()
        
        # Emplacements et localisations (pas de filtres de date car ce sont des données de référence)
        locations_count = location.objects.count()
        zones_count = zone.objects.count()
        emplacements_count = emplacement.objects.count()
        
        # Emplacements avec tag
        emplacements_avec_tag = emplacement.objects.filter(tag__isnull=False).count()
        
        # Tags disponibles
        tags_disponibles = tag.objects.filter(affecter=False).count()
        
        # Total fournisseurs et départements
        fournisseurs_count = fournisseur.objects.count()
        departements_count = departement.objects.count()
        
        return {
            'total_articles': total_articles,
            'total_items': total_items,
            'items_affectes': items_stats['affectes'],
            'items_non_affectes': items_stats['non_affectes'],
            'items_archives': items_archives,
            'total_locations': locations_count,
            'total_zones': zones_count,
            'total_emplacements': emplacements_count,
            'emplacements_avec_tag': emplacements_avec_tag,
            'tags_disponibles': tags_disponibles,
            'total_fournisseurs': fournisseurs_count,
            'total_departements': departements_count
        }
    
    def _calculate_value_kpis(self, date_filters=None):
        """Calcule les KPIs basés sur la valeur avec filtres de date"""
        
        # Appliquer les filtres de date aux articles
        articles_qs = article.objects.all()
        if date_filters:
            articles_qs = DateFilterHelper.apply_date_filters_to_queryset(articles_qs, date_filters)
        
        # Valeur totale des achats
        valeur_achats = articles_qs.aggregate(
            total=Sum(F('prix_achat') * F('qte_recue'), default=0)
        )['total'] or 0
        
        # Appliquer les filtres de date aux items
        items_qs = item.objects.select_related('article__produit').filter(archive=False)
        if date_filters:
            items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
        
        # Valeur résiduelle totale (calculée sur les items)
        valeur_residuelle_totale = sum(
            item.calculate_residual_value() or 0 for item in items_qs
        )
        
        # Valeur amortie
        valeur_amortie = valeur_achats - valeur_residuelle_totale
        
        # Taux d'amortissement
        taux_amortissement = (valeur_amortie / valeur_achats * 100) if valeur_achats > 0 else 0
        
        return {
            'valeur_totale_achats': float(valeur_achats),
            'valeur_residuelle_totale': float(valeur_residuelle_totale),
            'valeur_amortie': float(valeur_amortie),
            'taux_amortissement': round(taux_amortissement, 2)
        }
    
    def _calculate_performance_kpis(self, date_filters=None):
        """Calcule les KPIs de performance avec filtres de date"""
        
        # Appliquer les filtres de date aux items
        items_qs = item.objects.filter(archive=False)
        if date_filters:
            items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
        
        # Taux d'affectation
        items_stats = items_qs.aggregate(
            total=Count('id'),
            affectes=Count('id', filter=Q(statut='affecter'))
        )
        taux_affectation = (items_stats['affectes'] / items_stats['total'] * 100) if items_stats['total'] > 0 else 0
        
        # Taux d'utilisation des tags (pas de filtres de date car ce sont des données de référence)
        tags_stats = tag.objects.aggregate(
            total=Count('id'),
            affectes=Count('id', filter=Q(affecter=True))
        )
        taux_utilisation_tags = (tags_stats['affectes'] / tags_stats['total'] * 100) if tags_stats['total'] > 0 else 0
        
        # Taux d'occupation des emplacements (avec filtres sur les items)
        emplacements_qs = emplacement.objects.all()
        if date_filters:
            # Filtrer les emplacements qui ont des items correspondant aux critères de date
            items_filtres = item.objects.all()
            items_filtres = DateFilterHelper.apply_date_filters_to_queryset(items_filtres, date_filters)
            emplacements_avec_items = emplacements_qs.filter(item__in=items_filtres).distinct()
            emplacements_stats = {
                'total': emplacements_qs.count(),
                'avec_items': emplacements_avec_items.count()
            }
        else:
            emplacements_stats = emplacements_qs.aggregate(
                total=Count('id'),
                avec_items=Count('id', filter=Q(item__isnull=False))
            )
        
        taux_occupation = (emplacements_stats['avec_items'] / emplacements_stats['total'] * 100) if emplacements_stats['total'] > 0 else 0
        
        return {
            'taux_affectation': round(taux_affectation, 2),
            'taux_utilisation_tags': round(taux_utilisation_tags, 2),
            'taux_occupation_emplacements': round(taux_occupation, 2)
        }
    
    def _calculate_top_entities(self, date_filters=None):
        """Calcule les top 5 fournisseurs et départements avec filtres de date"""
        
        # Top 5 fournisseurs par valeur
        fournisseurs_qs = fournisseur.objects.annotate(
            total_value=Sum(F('article__prix_achat') * F('article__qte_recue'), default=0),
            total_qty=Sum('article__qte_recue', default=0)
        )
        
        # Appliquer les filtres de date aux articles des fournisseurs
        if date_filters:
            articles_filtres = article.objects.all()
            articles_filtres = DateFilterHelper.apply_date_filters_to_queryset(articles_filtres, date_filters)
            fournisseurs_qs = fournisseurs_qs.filter(article__in=articles_filtres).distinct()
        
        top_fournisseurs = fournisseurs_qs.order_by('-total_value')[:5]
        
        # Top 5 départements par valeur
        departements_qs = departement.objects.annotate(
            total_value=Sum(F('item__article__prix_achat'), default=0),
            items_count=Count('item', filter=Q(item__archive=False))
        )
        
        # Appliquer les filtres de date aux items des départements
        if date_filters:
            items_filtres = item.objects.filter(archive=False)
            items_filtres = DateFilterHelper.apply_date_filters_to_queryset(items_filtres, date_filters)
            departements_qs = departements_qs.filter(item__in=items_filtres).distinct()
        
        top_departements = departements_qs.order_by('-total_value')[:5]
        
        return {
            'top_fournisseurs': [
                {
                    'nom': f.nom,
                    'valeur_totale': float(f.total_value),
                    'quantite_totale': f.total_qty
                } for f in top_fournisseurs
            ],
            'top_departements': [
                {
                    'nom': d.nom,
                    'valeur_totale': float(d.total_value),
                    'items_count': d.items_count
                } for d in top_departements
            ]
        }
    
    def _calculate_inventory_status(self, date_filters=None):
        """Calcule l'état des inventaires avec filtres de date"""
        
        # Appliquer les filtres de date aux inventaires
        inventaires_qs = inventaire.objects.all()
        if date_filters:
            inventaires_qs = DateFilterHelper.apply_date_filters_to_queryset(inventaires_qs, date_filters)
        
        # Inventaires par statut
        inventaires_stats = inventaires_qs.aggregate(
            total=Count('id'),
            termines=Count('id', filter=Q(statut='Terminer')),
            en_cours=Count('id', filter=Q(statut='En cours')),
            en_attente=Count('id', filter=Q(statut='En attente'))
        )
        
        # Taux de complétion des inventaires en cours
        inventaires_en_cours = inventaires_qs.filter(statut='En cours')
        taux_completion = 0
        if inventaires_en_cours.exists():
            total_emplacements = inventaire_emplacement.objects.filter(
                inventaire__in=inventaires_en_cours
            ).count()
            emplacements_termines = inventaire_emplacement.objects.filter(
                inventaire__in=inventaires_en_cours,
                statut='Terminer'
            ).count()
            taux_completion = (emplacements_termines / total_emplacements * 100) if total_emplacements > 0 else 0
        
        return {
            'total_inventaires': inventaires_stats['total'],
            'inventaires_termines': inventaires_stats['termines'],
            'inventaires_en_cours': inventaires_stats['en_cours'],
            'inventaires_en_attente': inventaires_stats['en_attente'],
            'taux_completion': round(taux_completion, 2)
        }


class KPIQuantityAPIView(APIView):
    """
    API pour les KPIs basés sur la quantité
    
    GET /api/kpi/quantity/
    GET /api/kpi/quantity/?departement_id=1&periode=2024
    """
    
    def get(self, request):
        try:
            departement_id = request.query_params.get('departement_id')
            periode = request.query_params.get('periode')
            
            # Extraire les filtres de date
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            # Construire les filtres
            filters = {}
            if departement_id:
                filters['departement_id'] = departement_id
            
            kpis = self._calculate_quantity_kpis(filters, periode, date_filters)
            
            return Response(kpis, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans KPIQuantityAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des KPIs quantité: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_quantity_kpis(self, filters=None, periode=None, date_filters=None):
        """Calcule les KPIs de quantité avec filtres et filtres de date"""
        
        # Appliquer les filtres de date aux articles
        articles_qs = article.objects.all()
        if date_filters:
            articles_qs = DateFilterHelper.apply_date_filters_to_queryset(articles_qs, date_filters)
        
        # Articles par fournisseur - partir des items
        items_qs_for_fournisseur = item.objects.filter(archive=False).select_related('article', 'article__fournisseur')
        if date_filters:
            items_qs_for_fournisseur = DateFilterHelper.apply_date_filters_to_queryset(items_qs_for_fournisseur, date_filters)
        
        # Calculer les statistiques par fournisseur
        stats_by_fournisseur = {}
        for item_obj in items_qs_for_fournisseur:
            if item_obj.article and item_obj.article.fournisseur:
                fournisseur_id = item_obj.article.fournisseur.id
                fournisseur_nom = item_obj.article.fournisseur.nom
                
                if fournisseur_id not in stats_by_fournisseur:
                    stats_by_fournisseur[fournisseur_id] = {
                        'nom': fournisseur_nom,
                        'total_items': 0,
                        'total_articles': set(),
                        'valeur_totale': 0
                    }
                
                stats_by_fournisseur[fournisseur_id]['total_items'] += 1
                stats_by_fournisseur[fournisseur_id]['total_articles'].add(item_obj.article.id)
                stats_by_fournisseur[fournisseur_id]['valeur_totale'] += item_obj.article.prix_achat or 0
        
        # Convertir en liste et trier
        articles_fournisseur = sorted(
            [
                {
                    'nom': stats['nom'],
                    'total_articles': len(stats['total_articles']),
                    'total_value': stats['valeur_totale']
                } for stats in stats_by_fournisseur.values()
            ],
            key=lambda x: x['total_articles'],
            reverse=True
        )
        
        # Articles par famille (produit)
        articles_famille = produit.objects.annotate(
            total_articles=Sum('article__qte_recue', default=0),
            total_value=Sum(F('article__prix_achat') * F('article__qte_recue'), default=0)
        )
        if date_filters:
            articles_famille = articles_famille.filter(article__in=articles_qs).distinct()
        articles_famille = articles_famille.order_by('-total_articles')
        
        # Articles par catégorie
        articles_categorie = categorie.objects.annotate(
            total_articles=Sum('produit__article__qte_recue', default=0),
            total_value=Sum(F('produit__article__prix_achat') * F('produit__article__qte_recue'), default=0)
        )
        if date_filters:
            articles_categorie = articles_categorie.filter(produit__article__in=articles_qs).distinct()
        articles_categorie = articles_categorie.order_by('-total_articles')
        
        # Articles par nature
        articles_nature = nature.objects.annotate(
            total_articles=Sum('article__qte_recue', default=0),
            total_value=Sum(F('article__prix_achat') * F('article__qte_recue'), default=0)
        )
        if date_filters:
            articles_nature = articles_nature.filter(article__in=articles_qs).distinct()
        articles_nature = articles_nature.order_by('-total_articles')
        
        # Articles par marque
        articles_marque = marque.objects.annotate(
            total_articles=Sum('article__qte_recue', default=0),
            total_value=Sum(F('article__prix_achat') * F('article__qte_recue'), default=0)
        )
        if date_filters:
            articles_marque = articles_marque.filter(article__in=articles_qs).distinct()
        articles_marque = articles_marque.order_by('-total_articles')
        
        # Appliquer les filtres de date aux items
        items_qs = item.objects.filter(archive=False)
        if date_filters:
            items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
        
        # Items par département
        items_departement = departement.objects.annotate(
            items_count=Count('item', filter=Q(item__archive=False)),
            items_affectes=Count('item', filter=Q(item__archive=False, item__statut='affecter')),
            items_non_affectes=Count('item', filter=Q(item__archive=False, item__statut='non affecter'))
        )
        if date_filters:
            items_departement = items_departement.filter(item__in=items_qs).distinct()
        items_departement = items_departement.order_by('-items_count')
        
        # Items par emplacement
        items_emplacement = emplacement.objects.annotate(
            items_count=Count('item', filter=Q(item__archive=False)),
            items_affectes=Count('item', filter=Q(item__archive=False, item__statut='affecter'))
        )
        if date_filters:
            items_emplacement = items_emplacement.filter(item__in=items_qs).distinct()
        items_emplacement = items_emplacement.order_by('-items_count')
        
        # Items par zone
        items_zone = zone.objects.annotate(
            items_count=Count('emplacement__item', filter=Q(emplacement__item__archive=False)),
            emplacements_count=Count('emplacement')
        )
        if date_filters:
            items_zone = items_zone.filter(emplacement__item__in=items_qs).distinct()
        items_zone = items_zone.order_by('-items_count')
        
        # Items par location
        items_location = location.objects.annotate(
            items_count=Count('zone__emplacement__item', filter=Q(zone__emplacement__item__archive=False)),
            zones_count=Count('zone'),
            emplacements_count=Count('zone__emplacement')
        )
        if date_filters:
            items_location = items_location.filter(zone__emplacement__item__in=items_qs).distinct()
        items_location = items_location.order_by('-items_count')
        
        # Items par personne
        items_personne = Personne.objects.annotate(
            items_count=Count('item', filter=Q(item__archive=False)),
            items_value=Sum('item__article__prix_achat', default=0)
        )
        if date_filters:
            items_personne = items_personne.filter(item__in=items_qs).distinct()
        items_personne = items_personne.order_by('-items_count')
        
        return {
            'articles_par_fournisseur': [
                {
                    'fournisseur': f['nom'],
                    'total_articles': f['total_articles'],
                    'valeur_totale': float(f['total_value'])
                } for f in articles_fournisseur
            ],
            'articles_par_famille': [
                {
                    'famille': p.libelle,
                    'categorie': p.categorie.libelle,
                    'total_articles': p.total_articles,
                    'valeur_totale': float(p.total_value)
                } for p in articles_famille
            ],
            'articles_par_categorie': [
                {
                    'categorie': c.libelle,
                    'total_articles': c.total_articles,
                    'valeur_totale': float(c.total_value)
                } for c in articles_categorie
            ],
            'articles_par_nature': [
                {
                    'nature': n.libelle,
                    'total_articles': n.total_articles,
                    'valeur_totale': float(n.total_value)
                } for n in articles_nature
            ],
            'articles_par_marque': [
                {
                    'marque': m.nom,
                    'total_articles': m.total_articles,
                    'valeur_totale': float(m.total_value)
                } for m in articles_marque
            ],
            'items_par_departement': [
                {
                    'departement': d.nom,
                    'items_count': d.items_count,
                    'items_affectes': d.items_affectes,
                    'items_non_affectes': d.items_non_affectes
                } for d in items_departement
            ],
            'items_par_emplacement': [
                {
                    'emplacement': e.nom,
                    'zone': e.zone.nom,
                    'location': e.zone.location.nom,
                    'items_count': e.items_count,
                    'items_affectes': e.items_affectes
                } for e in items_emplacement
            ],
            'items_par_zone': [
                {
                    'zone': z.nom,
                    'location': z.location.nom,
                    'items_count': z.items_count,
                    'emplacements_count': z.emplacements_count
                } for z in items_zone
            ],
            'items_par_location': [
                {
                    'location': l.nom,
                    'items_count': l.items_count,
                    'zones_count': l.zones_count,
                    'emplacements_count': l.emplacements_count
                } for l in items_location
            ],
            'items_par_personne': [
                {
                    'personne': f"{p.prenom} {p.nom}",
                    'items_count': p.items_count,
                    'valeur_totale': float(p.items_value)
                } for p in items_personne
            ]
        }


class KPIValueAPIView(APIView):
    """
    API pour les KPIs basés sur la valeur
    
    GET /api/kpi/value/
    GET /api/kpi/value/?departement_id=1&periode=2024
    """
    
    def get(self, request):
        try:
            departement_id = request.query_params.get('departement_id')
            periode = request.query_params.get('periode')
            
            # Extraire les filtres de date
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            kpis = self._calculate_value_kpis(departement_id, periode, date_filters)
            
            return Response(kpis, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans KPIValueAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des KPIs valeur: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_value_kpis(self, departement_id=None, periode=None, date_filters=None):
        """Calcule les KPIs de valeur avec filtres et filtres de date"""
        
        # Appliquer les filtres de date aux articles
        articles_qs = article.objects.all()
        if date_filters:
            articles_qs = DateFilterHelper.apply_date_filters_to_queryset(articles_qs, date_filters)
        
        # Valeur par fournisseur - partir des items
        items_qs_for_valeur = item.objects.filter(archive=False).select_related('article', 'article__fournisseur')
        if date_filters:
            items_qs_for_valeur = DateFilterHelper.apply_date_filters_to_queryset(items_qs_for_valeur, date_filters)
        
        # Calculer les statistiques par fournisseur
        stats_by_fournisseur_value = {}
        for item_obj in items_qs_for_valeur:
            if item_obj.article and item_obj.article.fournisseur:
                fournisseur_id = item_obj.article.fournisseur.id
                fournisseur_nom = item_obj.article.fournisseur.nom
                
                if fournisseur_id not in stats_by_fournisseur_value:
                    stats_by_fournisseur_value[fournisseur_id] = {
                        'nom': fournisseur_nom,
                        'total_value': 0,
                        'total_qty': 0
                    }
                
                prix = item_obj.article.prix_achat or 0
                stats_by_fournisseur_value[fournisseur_id]['total_value'] += prix
                stats_by_fournisseur_value[fournisseur_id]['total_qty'] += 1
        
        # Convertir en liste et trier
        valeur_fournisseur = sorted(
            stats_by_fournisseur_value.values(),
            key=lambda x: x['total_value'],
            reverse=True
        )
        
        # Valeur par famille (produit)
        valeur_famille = produit.objects.annotate(
            total_value=Sum(F('article__prix_achat') * F('article__qte_recue'), default=0),
            total_qty=Sum('article__qte_recue', default=0)
        )
        if date_filters:
            valeur_famille = valeur_famille.filter(article__in=articles_qs).distinct()
        valeur_famille = valeur_famille.order_by('-total_value')
        
        # Valeur par catégorie
        valeur_categorie = categorie.objects.annotate(
            total_value=Sum(F('produit__article__prix_achat') * F('produit__article__qte_recue'), default=0),
            total_qty=Sum('produit__article__qte_recue', default=0)
        )
        if date_filters:
            valeur_categorie = valeur_categorie.filter(produit__article__in=articles_qs).distinct()
        valeur_categorie = valeur_categorie.order_by('-total_value')
        
        # Valeur par nature
        valeur_nature = nature.objects.annotate(
            total_value=Sum(F('article__prix_achat') * F('article__qte_recue'), default=0),
            total_qty=Sum('article__qte_recue', default=0)
        )
        if date_filters:
            valeur_nature = valeur_nature.filter(article__in=articles_qs).distinct()
        valeur_nature = valeur_nature.order_by('-total_value')
        
        # Valeur par marque
        valeur_marque = marque.objects.annotate(
            total_value=Sum(F('article__prix_achat') * F('article__qte_recue'), default=0),
            total_qty=Sum('article__qte_recue', default=0)
        )
        if date_filters:
            valeur_marque = valeur_marque.filter(article__in=articles_qs).distinct()
        valeur_marque = valeur_marque.order_by('-total_value')
        
        # Appliquer les filtres de date aux items
        items_qs = item.objects.filter(archive=False)
        if date_filters:
            items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
        
        # Valeur par département
        valeur_departement = departement.objects.annotate(
            total_value=Sum('item__article__prix_achat', default=0),
            items_count=Count('item', filter=Q(item__archive=False))
        )
        if date_filters:
            valeur_departement = valeur_departement.filter(item__in=items_qs).distinct()
        valeur_departement = valeur_departement.order_by('-total_value')
        
        # Valeur par location
        valeur_location = location.objects.annotate(
            total_value=Sum('zone__emplacement__item__article__prix_achat', default=0),
            items_count=Count('zone__emplacement__item', filter=Q(zone__emplacement__item__archive=False))
        )
        if date_filters:
            valeur_location = valeur_location.filter(zone__emplacement__item__in=items_qs).distinct()
        valeur_location = valeur_location.order_by('-total_value')
        
        # Valeur par zone
        valeur_zone = zone.objects.annotate(
            total_value=Sum('emplacement__item__article__prix_achat', default=0),
            items_count=Count('emplacement__item', filter=Q(emplacement__item__archive=False))
        )
        if date_filters:
            valeur_zone = valeur_zone.filter(emplacement__item__in=items_qs).distinct()
        valeur_zone = valeur_zone.order_by('-total_value')
        
        # Valeur par emplacement
        valeur_emplacement = emplacement.objects.annotate(
            total_value=Sum('item__article__prix_achat', default=0),
            items_count=Count('item', filter=Q(item__archive=False))
        )
        if date_filters:
            valeur_emplacement = valeur_emplacement.filter(item__in=items_qs).distinct()
        valeur_emplacement = valeur_emplacement.order_by('-total_value')
        
        # Valeur résiduelle par département
        valeur_residuelle_departement = []
        for dept in departement.objects.all():
            items = item.objects.filter(departement=dept, archive=False).select_related('article__produit')
            if date_filters:
                items = DateFilterHelper.apply_date_filters_to_queryset(items, date_filters)
            valeur_residuelle = sum(item.calculate_residual_value() or 0 for item in items)
            valeur_residuelle_departement.append({
                'departement': dept.nom,
                'valeur_residuelle': float(valeur_residuelle),
                'items_count': items.count()
            })
        
        # Valeur résiduelle par emplacement
        valeur_residuelle_emplacement = []
        for emp in emplacement.objects.all():
            items = item.objects.filter(emplacement=emp, archive=False).select_related('article__produit')
            if date_filters:
                items = DateFilterHelper.apply_date_filters_to_queryset(items, date_filters)
            valeur_residuelle = sum(item.calculate_residual_value() or 0 for item in items)
            valeur_residuelle_emplacement.append({
                'emplacement': emp.nom,
                'zone': emp.zone.nom,
                'location': emp.zone.location.nom,
                'valeur_residuelle': float(valeur_residuelle),
                'items_count': items.count()
            })
        
        # Valeur résiduelle par famille
        valeur_residuelle_famille = []
        for prod in produit.objects.all():
            items = item.objects.filter(article__produit=prod, archive=False).select_related('article__produit')
            if date_filters:
                items = DateFilterHelper.apply_date_filters_to_queryset(items, date_filters)
            valeur_residuelle = sum(item.calculate_residual_value() or 0 for item in items)
            valeur_residuelle_famille.append({
                'famille': prod.libelle,
                'categorie': prod.categorie.libelle,
                'valeur_residuelle': float(valeur_residuelle),
                'items_count': items.count()
            })
        
        return {
            'valeur_par_fournisseur': [
                {
                    'fournisseur': f['nom'],
                    'valeur_totale': float(f['total_value']),
                    'quantite_totale': f['total_qty']
                } for f in valeur_fournisseur
            ],
            'valeur_par_famille': [
                {
                    'famille': p.libelle,
                    'categorie': p.categorie.libelle,
                    'valeur_totale': float(p.total_value),
                    'quantite_totale': p.total_qty
                } for p in valeur_famille
            ],
            'valeur_par_categorie': [
                {
                    'categorie': c.libelle,
                    'valeur_totale': float(c.total_value),
                    'quantite_totale': c.total_qty
                } for c in valeur_categorie
            ],
            'valeur_par_nature': [
                {
                    'nature': n.libelle,
                    'valeur_totale': float(n.total_value),
                    'quantite_totale': n.total_qty
                } for n in valeur_nature
            ],
            'valeur_par_marque': [
                {
                    'marque': m.nom,
                    'valeur_totale': float(m.total_value),
                    'quantite_totale': m.total_qty
                } for m in valeur_marque
            ],
            'valeur_par_departement': [
                {
                    'departement': d.nom,
                    'valeur_totale': float(d.total_value),
                    'items_count': d.items_count
                } for d in valeur_departement
            ],
            'valeur_par_location': [
                {
                    'location': l.nom,
                    'valeur_totale': float(l.total_value),
                    'items_count': l.items_count
                } for l in valeur_location
            ],
            'valeur_par_zone': [
                {
                    'zone': z.nom,
                    'location': z.location.nom,
                    'valeur_totale': float(z.total_value),
                    'items_count': z.items_count
                } for z in valeur_zone
            ],
            'valeur_par_emplacement': [
                {
                    'emplacement': e.nom,
                    'zone': e.zone.nom,
                    'location': e.zone.location.nom,
                    'valeur_totale': float(e.total_value),
                    'items_count': e.items_count
                } for e in valeur_emplacement
            ],
            'valeur_residuelle_par_departement': sorted(
                valeur_residuelle_departement, 
                key=lambda x: x['valeur_residuelle'], 
                reverse=True
            ),
            'valeur_residuelle_par_emplacement': sorted(
                valeur_residuelle_emplacement, 
                key=lambda x: x['valeur_residuelle'], 
                reverse=True
            ),
            'valeur_residuelle_par_famille': sorted(
                valeur_residuelle_famille, 
                key=lambda x: x['valeur_residuelle'], 
                reverse=True
            )
        }


class KPITemporalAPIView(APIView):
    """
    API pour les analyses temporelles des KPIs
    
    GET /api/kpi/temporal/
    GET /api/kpi/temporal/?periode=2024&granularite=month
    """
    
    def get(self, request):
        try:
            periode = request.query_params.get('periode', str(datetime.now().year))
            granularite = request.query_params.get('granularite', 'month')  # month, quarter, year
            
            # Extraire les filtres de date
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            kpis = self._calculate_temporal_kpis(periode, granularite, date_filters)
            
            return Response(kpis, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans KPITemporalAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des KPIs temporels: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_temporal_kpis(self, periode, granularite):
        """Calcule les KPIs temporels"""
        
        # Évolution des achats
        if granularite == 'month':
            trunc_func = TruncMonth('date_achat')
        elif granularite == 'quarter':
            trunc_func = TruncQuarter('date_achat')
        else:  # year
            trunc_func = TruncYear('date_achat')
        
        evolution_achats = article.objects.annotate(
            periode=trunc_func
        ).values('periode').annotate(
            total_value=Sum(F('prix_achat') * F('qte_recue'), default=0),
            total_qty=Sum('qte_recue', default=0),
            count_articles=Count('id')
        ).order_by('periode')
        
        # Évolution du taux d'affectation
        evolution_affectation = []
        for month in range(1, 13):
            items_stats = item.objects.filter(
                created_at__year=periode,
                created_at__month=month
            ).aggregate(
                total=Count('id'),
                affectes=Count('id', filter=Q(statut='affecter'))
            )
            taux = (items_stats['affectes'] / items_stats['total'] * 100) if items_stats['total'] > 0 else 0
            evolution_affectation.append({
                'mois': month,
                'taux_affectation': round(taux, 2),
                'total_items': items_stats['total']
            })
        
        # Évolution de la valeur du parc
        evolution_valeur_parc = []
        for month in range(1, 13):
            valeur_mois = article.objects.filter(
                date_achat__year=periode,
                date_achat__month=month
            ).aggregate(
                total=Sum(F('prix_achat') * F('qte_recue'), default=0)
            )['total'] or 0
            evolution_valeur_parc.append({
                'mois': month,
                'valeur_achats': float(valeur_mois)
            })
        
        # Délai moyen entre achat et réception
        delai_moyen = article.objects.filter(
            date_achat__year=periode
        ).aggregate(
            delai_moyen=Avg(F('date_reception') - F('date_achat'))
        )['delai_moyen']
        
        # Durée moyenne des inventaires
        duree_moyenne_inventaires = inventaire.objects.filter(
            date_creation__year=periode,
            statut='Terminer'
        ).aggregate(
            duree_moyenne=Avg(F('date_fin') - F('date_debut'))
        )['duree_moyenne']
        
        return {
            'evolution_achats': list(evolution_achats),
            'evolution_affectation': evolution_affectation,
            'evolution_valeur_parc': evolution_valeur_parc,
            'delai_moyen_achat_reception': float(delai_moyen.days) if delai_moyen else 0,
            'duree_moyenne_inventaires': float(duree_moyenne_inventaires.days) if duree_moyenne_inventaires else 0
        }


class KPITransfersAPIView(APIView):
    """
    API pour les KPIs des transferts et opérations
    
    GET /api/kpi/transfers/
    """
    
    def get(self, request):
        try:
            kpis = self._calculate_transfers_kpis()
            
            return Response(kpis, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors du calcul des KPIs transferts: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_transfers_kpis(self):
        """Calcule les KPIs des transferts"""
        
        # Total transferts
        total_transferts = TransferHistorique.objects.count()
        
        # Transferts par item
        transferts_par_item = item.objects.annotate(
            transferts_count=Count('transferhistorique')
        ).order_by('-transferts_count')
        
        # Transferts d'emplacement
        transferts_emplacement = TransferHistorique.objects.filter(
            new_emplacement__isnull=False
        ).count()
        
        # Transferts de personne
        transferts_personne = TransferHistorique.objects.filter(
            new_personne__isnull=False
        ).count()
        
        # Transferts de département
        transferts_departement = TransferHistorique.objects.filter(
            new_departement__isnull=False
        ).count()
        
        # Total items archivés
        total_items_archives = ArchiveItem.objects.count()
        
        # Valeur totale des opérations
        valeur_operations = operation_article.objects.aggregate(
            total=Sum('prix', default=0)
        )['total'] or 0
        
        # Opérations par type (si on avait un champ type)
        operations_stats = operation_article.objects.aggregate(
            total_operations=Count('id'),
            valeur_totale=Sum('prix', default=0)
        )
        
        return {
            'total_transferts': total_transferts,
            'transferts_par_item': [
                {
                    'item': f"{t.item.reference_auto} - {t.item.article.designation}",
                    'transferts_count': t.transferts_count
                } for t in transferts_par_item[:10]  # Top 10
            ],
            'transferts_emplacement': transferts_emplacement,
            'transferts_personne': transferts_personne,
            'transferts_departement': transferts_departement,
            'total_items_archives': total_items_archives,
            'valeur_totale_operations': float(valeur_operations),
            'operations_stats': {
                'total_operations': operations_stats['total_operations'],
                'valeur_totale': float(operations_stats['valeur_totale'])
            }
        }
