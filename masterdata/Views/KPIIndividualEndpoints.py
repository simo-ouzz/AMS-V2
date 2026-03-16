"""
Endpoints individuels pour chaque KPI

Ce module implémente des endpoints séparés pour chaque KPI spécifique,
permettant un accès direct et ciblé à chaque métrique.

Structure:
- Chaque KPI a son propre endpoint
- Filtres par date complets pour chaque endpoint
- Réponses optimisées pour chaque métrique
- Documentation claire pour chaque endpoint
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, F, Q, Avg
from django.db.models.functions import TruncMonth, TruncYear, TruncQuarter
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
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


# =============================================================================
# KPIs BASÉS SUR LA QUANTITÉ
# =============================================================================

class TotalArticlesAPIView(APIView):
    """
    Endpoint pour le KPI: Total Articles
    
    GET /api/kpi/total-articles/
    
    Retourne le nombre total d'articles achetés (qte_recue)
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            articles_qs = article.objects.all()
            if date_filters:
                articles_qs = DateFilterHelper.apply_date_filters_to_queryset(articles_qs, date_filters)
            
            total_articles = articles_qs.aggregate(
                total=Sum('qte_recue', default=0)
            )['total'] or 0
            
            return Response({
                'kpi': 'total_articles',
                'value': total_articles,
                'description': 'Nombre total d\'articles achetés',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans TotalArticlesAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul du total articles: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticlesParFournisseurAPIView(APIView):
    """
    Endpoint pour le KPI: Articles par Fournisseur
    
    GET /api/kpi/articles-par-fournisseur/
    
    Retourne la répartition des articles par fournisseur
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            # Partir des items pour obtenir le vrai nombre d'items par fournisseur
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
                            'total_articles': 0,
                            'valeur_totale': 0.0
                        }
                    
                    stats_by_fournisseur[fournisseur_id]['total_articles'] += 1
                    stats_by_fournisseur[fournisseur_id]['valeur_totale'] += float(item_obj.article.prix_achat or 0)
            
            # Convertir en liste et trier (par total_articles comme avant)
            data = [
                {
                    'fournisseur': stats['nom'],
                    'total_articles': stats['total_articles'],
                    'valeur_totale': float(stats['valeur_totale'])
                } for stats in sorted(stats_by_fournisseur.values(), key=lambda x: x['total_articles'], reverse=True)
            ]
            
            return Response({
                'kpi': 'articles_par_fournisseur',
                'data': data,
                'description': 'Répartition des articles par fournisseur',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ArticlesParFournisseurAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des articles par fournisseur: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticlesParFamilleAPIView(APIView):
    """
    Endpoint pour le KPI: Articles par Famille
    
    GET /api/kpi/articles-par-famille/
    
    Retourne la répartition des articles par famille de produit
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            # Partir des items pour obtenir le vrai nombre d'items par famille
            items_qs = item.objects.filter(archive=False).select_related('article', 'article__produit', 'article__produit__categorie')
            if date_filters:
                items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
            
            # Calculer les statistiques par famille
            stats_by_famille = {}
            for item_obj in items_qs:
                if item_obj.article and item_obj.article.produit:
                    famille_id = item_obj.article.produit.id
                    famille_libelle = item_obj.article.produit.libelle
                    categorie_libelle = item_obj.article.produit.categorie.libelle if item_obj.article.produit.categorie else ''
                    
                    if famille_id not in stats_by_famille:
                        stats_by_famille[famille_id] = {
                            'libelle': famille_libelle,
                            'categorie': categorie_libelle,
                            'total_articles': 0,
                            'valeur_totale': 0.0
                        }
                    
                    stats_by_famille[famille_id]['total_articles'] += 1
                    stats_by_famille[famille_id]['valeur_totale'] += float(item_obj.article.prix_achat or 0)
            
            # Convertir en liste et trier (par total_articles comme avant)
            data = [
                {
                    'famille': stats['libelle'],
                    'categorie': stats['categorie'],
                    'total_articles': stats['total_articles'],
                    'valeur_totale': float(stats['valeur_totale'])
                } for stats in sorted(stats_by_famille.values(), key=lambda x: x['total_articles'], reverse=True)
            ]
            
            return Response({
                'kpi': 'articles_par_famille',
                'data': data,
                'description': 'Répartition des articles par famille de produit',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ArticlesParFamilleAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des articles par famille: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticlesParCategorieAPIView(APIView):
    """
    Endpoint pour le KPI: Articles par Catégorie
    
    GET /api/kpi/articles-par-categorie/
    
    Retourne la répartition des articles par catégorie
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            # Partir des items pour obtenir le vrai nombre d'items par catégorie
            items_qs = item.objects.filter(archive=False).select_related('article', 'article__produit', 'article__produit__categorie')
            if date_filters:
                items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
            
            # Calculer les statistiques par catégorie
            stats_by_categorie = {}
            for item_obj in items_qs:
                if item_obj.article and item_obj.article.produit and item_obj.article.produit.categorie:
                    categorie_id = item_obj.article.produit.categorie.id
                    categorie_libelle = item_obj.article.produit.categorie.libelle
                    
                    if categorie_id not in stats_by_categorie:
                        stats_by_categorie[categorie_id] = {
                            'libelle': categorie_libelle,
                            'total_articles': 0,
                            'valeur_totale': 0.0
                        }
                    
                    stats_by_categorie[categorie_id]['total_articles'] += 1
                    stats_by_categorie[categorie_id]['valeur_totale'] += float(item_obj.article.prix_achat or 0)
            
            # Convertir en liste et trier
            data = [
                {
                    'categorie': stats['libelle'],
                    'total_articles': stats['total_articles'],
                    'valeur_totale': float(stats['valeur_totale'])
                } for stats in sorted(stats_by_categorie.values(), key=lambda x: x['total_articles'], reverse=True)
            ]
            
            return Response({
                'kpi': 'articles_par_categorie',
                'data': data,
                'description': 'Répartition des articles par catégorie',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ArticlesParCategorieAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des articles par catégorie: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticlesParNatureAPIView(APIView):
    """
    Endpoint pour le KPI: Articles par Nature
    
    GET /api/kpi/articles-par-nature/
    
    Retourne la répartition des articles par nature
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            # Partir des items pour obtenir le vrai nombre d'items par nature
            items_qs = item.objects.filter(archive=False).select_related('article', 'article__nature')
            if date_filters:
                items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
            
            # Calculer les statistiques par nature
            stats_by_nature = {}
            for item_obj in items_qs:
                if item_obj.article and item_obj.article.nature:
                    nature_id = item_obj.article.nature.id
                    nature_libelle = item_obj.article.nature.libelle
                    
                    if nature_id not in stats_by_nature:
                        stats_by_nature[nature_id] = {
                            'libelle': nature_libelle,
                            'total_articles': 0,
                            'valeur_totale': 0.0
                        }
                    
                    stats_by_nature[nature_id]['total_articles'] += 1
                    stats_by_nature[nature_id]['valeur_totale'] += float(item_obj.article.prix_achat or 0)
            
            # Convertir en liste et trier
            data = [
                {
                    'nature': stats['libelle'],
                    'total_articles': stats['total_articles'],
                    'valeur_totale': float(stats['valeur_totale'])
                } for stats in sorted(stats_by_nature.values(), key=lambda x: x['total_articles'], reverse=True)
            ]
            
            return Response({
                'kpi': 'articles_par_nature',
                'data': data,
                'description': 'Répartition des articles par nature',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ArticlesParNatureAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des articles par nature: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TotalTransfertsAPIView(APIView):
    """
    Endpoint pour le KPI: Total Transferts
    
    GET /api/kpi/total-transferts/
    
    Retourne le nombre total de transferts
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            transferts_qs = TransferHistorique.objects.all()
            if date_filters:
                transferts_qs = DateFilterHelper.apply_date_filters_to_queryset(transferts_qs, date_filters)
            
            total_transferts = transferts_qs.count()
            
            return Response({
                'kpi': 'total_transferts',
                'value': total_transferts,
                'description': 'Nombre total de transferts',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans TotalTransfertsAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul du total transferts: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# KPIs BASÉS SUR LA VALEUR
# =============================================================================

class ValeurTotaleAchatsAPIView(APIView):
    """
    Endpoint pour le KPI: Valeur Totale des Achats
    
    GET /api/kpi/valeur-totale-achats/
    
    Retourne la valeur totale des achats (prix_achat * qte_recue)
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            articles_qs = article.objects.all()
            if date_filters:
                articles_qs = DateFilterHelper.apply_date_filters_to_queryset(articles_qs, date_filters)
            
            valeur_totale = articles_qs.aggregate(
                total=Sum(F('prix_achat') * F('qte_recue'), default=0)
            )['total'] or 0
            
            return Response({
                'kpi': 'valeur_totale_achats',
                'value': float(valeur_totale),
                'description': 'Valeur totale des achats (prix_achat * qte_recue)',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ValeurTotaleAchatsAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul de la valeur totale des achats: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ValeurParFournisseurAPIView(APIView):
    """
    Endpoint pour le KPI: Valeur par Fournisseur
    
    GET /api/kpi/valeur-par-fournisseur/
    
    Retourne la valeur des achats par fournisseur
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            # Partir des items pour obtenir la vraie valeur par fournisseur
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
                            'valeur_totale': 0,
                            'quantite_totale': 0
                        }
                    
                    prix = item_obj.article.prix_achat or 0
                    stats_by_fournisseur[fournisseur_id]['valeur_totale'] += prix
                    stats_by_fournisseur[fournisseur_id]['quantite_totale'] += 1
            
            # Convertir en liste et trier
            data = [
                {
                    'fournisseur': stats['nom'],
                    'valeur_totale': float(stats['valeur_totale']),
                    'quantite_totale': stats['quantite_totale']
                } for stats in sorted(stats_by_fournisseur.values(), key=lambda x: x['valeur_totale'], reverse=True)
            ]
            
            return Response({
                'kpi': 'valeur_par_fournisseur',
                'data': data,
                'description': 'Valeur des achats par fournisseur',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ValeurParFournisseurAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul de la valeur par fournisseur: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# KPIs DE PERFORMANCE
# =============================================================================

class TauxAffectationAPIView(APIView):
    """
    Endpoint pour le KPI: Taux d'Affectation
    
    GET /api/kpi/taux-affectation/
    
    Retourne le taux d'affectation des items
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            items_qs = item.objects.filter(archive=False)
            if date_filters:
                items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
            
            items_stats = items_qs.aggregate(
                total=Count('id'),
                affectes=Count('id', filter=Q(statut='affecter'))
            )
            
            taux_affectation = (items_stats['affectes'] / items_stats['total'] * 100) if items_stats['total'] > 0 else 0
            
            return Response({
                'kpi': 'taux_affectation',
                'value': round(taux_affectation, 2),
                'total_items': items_stats['total'],
                'items_affectes': items_stats['affectes'],
                'items_non_affectes': items_stats['total'] - items_stats['affectes'],
                'description': 'Taux d\'affectation des items',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans TauxAffectationAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul du taux d\'affectation: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ValeurResiduelleTotaleAPIView(APIView):
    """
    Endpoint pour le KPI: Valeur Résiduelle Totale
    
    GET /api/kpi/valeur-residuelle-totale/
    
    Retourne la valeur résiduelle totale des items
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            items_qs = item.objects.select_related('article__produit').filter(archive=False)
            if date_filters:
                items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
            
            valeur_residuelle_totale = sum(
                item.calculate_residual_value() or 0 for item in items_qs
            )
            
            return Response({
                'kpi': 'valeur_residuelle_totale',
                'value': float(valeur_residuelle_totale),
                'description': 'Valeur résiduelle totale des items après amortissement',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ValeurResiduelleTotaleAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul de la valeur résiduelle totale: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ItemsParDepartementAPIView(APIView):
    """
    Endpoint pour le KPI: Items par Département
    
    GET /api/kpi/items-par-departement/
    
    Retourne la répartition des items par département
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            items_qs = item.objects.filter(archive=False)
            if date_filters:
                items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
            
            items_departement = departement.objects.annotate(
                items_count=Count('item', filter=Q(item__archive=False)),
                items_affectes=Count('item', filter=Q(item__archive=False, item__statut='affecter')),
                items_non_affectes=Count('item', filter=Q(item__archive=False, item__statut='non affecter'))
            ).filter(item__in=items_qs).distinct().order_by('-items_count')
            
            data = [
                {
                    'departement': d.nom,
                    'items_count': d.items_count,
                    'items_affectes': d.items_affectes,
                    'items_non_affectes': d.items_non_affectes
                } for d in items_departement
            ]
            
            return Response({
                'kpi': 'items_par_departement',
                'data': data,
                'description': 'Répartition des items par département',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ItemsParDepartementAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des items par département: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TotalItemsAPIView(APIView):
    """
    Endpoint pour le KPI: Total Items
    
    GET /api/kpi/total-items/
    
    Retourne le nombre total d'items actifs
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            items_qs = item.objects.filter(archive=False)
            if date_filters:
                items_qs = DateFilterHelper.apply_date_filters_to_queryset(items_qs, date_filters)
            
            total_items = items_qs.count()
            
            return Response({
                'kpi': 'total_items',
                'value': total_items,
                'description': 'Nombre total d\'items actifs',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans TotalItemsAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul du total items: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ItemsArchivesAPIView(APIView):
    """
    Endpoint pour le KPI: Items Archivés
    
    GET /api/kpi/items-archives/
    
    Retourne le nombre d'items archivés
    """
    
    def get(self, request):
        try:
            date_filters = DateFilterHelper.extract_date_filters_from_params(request.query_params)
            
            items_archives_qs = item.objects.filter(archive=True)
            if date_filters:
                items_archives_qs = DateFilterHelper.apply_date_filters_to_queryset(items_archives_qs, date_filters)
            
            total_archives = items_archives_qs.count()
            
            return Response({
                'kpi': 'items_archives',
                'value': total_archives,
                'description': 'Nombre d\'items archivés',
                'filtres_appliques': date_filters,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans ItemsArchivesAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des items archivés: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TotalEmplacementsAPIView(APIView):
    """
    Endpoint pour le KPI: Total Emplacements
    
    GET /api/kpi/total-emplacements/
    
    Retourne le nombre total d'emplacements
    """
    
    def get(self, request):
        try:
            total_emplacements = emplacement.objects.count()
            
            return Response({
                'kpi': 'total_emplacements',
                'value': total_emplacements,
                'description': 'Nombre total d\'emplacements',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans TotalEmplacementsAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul du total emplacements: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TotalLocationsAPIView(APIView):
    """
    Endpoint pour le KPI: Total Locations
    
    GET /api/kpi/total-locations/
    
    Retourne le nombre total de locations
    """
    
    def get(self, request):
        try:
            total_locations = location.objects.count()
            
            return Response({
                'kpi': 'total_locations',
                'value': total_locations,
                'description': 'Nombre total de locations',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans TotalLocationsAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul du total locations: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TotalZonesAPIView(APIView):
    """
    Endpoint pour le KPI: Total Zones
    
    GET /api/kpi/total-zones/
    
    Retourne le nombre total de zones
    """
    
    def get(self, request):
        try:
            total_zones = zone.objects.count()
            
            return Response({
                'kpi': 'total_zones',
                'value': total_zones,
                'description': 'Nombre total de zones',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans TotalZonesAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul du total zones: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TagsAffectationAPIView(APIView):
    """
    Endpoint pour le KPI: Tags Affectés et Non Affectés
    
    GET /api/kpi/tags-affectation/
    
    Retourne le nombre de tags affectés et non affectés
    """
    
    def get(self, request):
        try:
            tags_stats = tag.objects.aggregate(
                total=Count('id'),
                affectes=Count('id', filter=Q(affecter=True)),
                non_affectes=Count('id', filter=Q(affecter=False))
            )
            
            taux_affectation = (tags_stats['affectes'] / tags_stats['total'] * 100) if tags_stats['total'] > 0 else 0
            
            return Response({
                'kpi': 'tags_affectation',
                'total_tags': tags_stats['total'],
                'tags_affectes': tags_stats['affectes'],
                'tags_non_affectes': tags_stats['non_affectes'],
                'taux_affectation': round(taux_affectation, 2),
                'description': 'Répartition des tags par statut d\'affectation',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur dans TagsAffectationAPIView: {str(e)}")
            return Response(
                {'error': f'Erreur lors du calcul des tags affectés/non affectés: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )