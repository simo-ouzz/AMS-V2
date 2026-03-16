"""
API pour le Dashboard Principal des KPIs

Ce module implémente l'API principale du dashboard qui retourne tous les KPIs critiques
en une seule requête pour optimiser les performances du frontend.

Fonctionnalités:
- Tous les KPIs critiques en une seule requête
- Cache Redis pour optimiser les performances
- Filtres par date avec tous les opérateurs
- Métriques de quantité, valeur, performance et inventaires
- Top 5 fournisseurs et départements
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, F, Q
from django.core.cache import cache
from django.utils import timezone
import logging

from masterdata.Views.DateFilterHelper import DateFilterHelper
from masterdata.models import (
    article, item, emplacement, zone, location, departement, 
    fournisseur, categorie, nature, marque, produit, inventaire,
    inventaire_emplacement, detail_inventaire, ArchiveItem,
    operation_article, TransferHistorique, tag, tagEmplacement,
    Personne
)

logger = logging.getLogger(__name__)


class KPIDashboardAPIView(APIView):
    """
    API principale pour le dashboard - Retourne tous les KPIs critiques
    
    GET /api/kpi/dashboard/
    
    Paramètres de filtrage par date:
    - date_achat_exact, date_achat_gte, date_achat_lte, date_achat_between
    - date_reception_exact, date_reception_gte, date_reception_lte, date_reception_between
    - date_affectation_exact, date_affectation_gte, date_affectation_lte, date_affectation_between
    - date_archive_exact, date_archive_gte, date_archive_lte, date_archive_between
    - created_at_exact, created_at_gte, created_at_lte, created_at_between
    - updated_at_exact, updated_at_gte, updated_at_lte, updated_at_between
    
    Exemples:
    - GET /api/kpi/dashboard/
    - GET /api/kpi/dashboard/?date_achat_gte=2024-01-01&date_achat_lte=2024-12-31
    - GET /api/kpi/dashboard/?date_achat_between=2024-01-01,2024-12-31&created_at_year=2024
    
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
        
        # Top 5 fournisseurs par valeur - partir des items
        items_qs = item.objects.filter(archive=False).select_related('article', 'article__fournisseur')
        if date_filters:
            items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
        
        # Calculer les statistiques par fournisseur
        stats_by_fournisseur = {}
        for item_obj in items_qs:
            if item_obj.article and item_obj.article.fournisseur:
                fournisseur_id = item_obj.article.fournisseur.id
                fournisseur_nom = item_obj.article.fournisseur.nom
                
                if fournisseur_id not in stats_by_fournisseur:
                    stats_by_fournisseur[fournisseur_id] = {
                        'nom': fournisseur_nom,
                        'total_value': 0,
                        'total_qty': 0
                    }
                
                prix = item_obj.article.prix_achat or 0
                stats_by_fournisseur[fournisseur_id]['total_value'] += prix
                stats_by_fournisseur[fournisseur_id]['total_qty'] += 1
        
        # Convertir en liste et prendre top 5
        top_fournisseurs = sorted(
            stats_by_fournisseur.values(), 
            key=lambda x: x['total_value'], 
            reverse=True
        )[:5]
        
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
                    'nom': f['nom'],
                    'valeur_totale': float(f['total_value']),
                    'quantite_totale': f['total_qty']
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
