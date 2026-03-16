"""
KPIs Valeur & Quantité - Vue d'ensemble financière et stock

Ce module fournit les KPIs essentiels pour le suivi :
- Valeur financière (acquisition, résiduelle, amortissement)
- Quantités (stock, disponibilité, répartition)
- Analyses croisées valeur × quantité

Endpoints :
- /kpi/valeur/acquisition/ - Valeur totale acquisition
- /kpi/valeur/stock-vs-affectee/ - Capital stock vs affecté
- /kpi/quantite/globale/ - Vue quantités globale
- /kpi/quantite/par-categorie/ - Quantités par catégorie
- /kpi/quantite/par-departement/ - Quantités par département
- /kpi/valeur/par-fournisseur/ - Analyse fournisseurs
- /kpi/stock/critique/ - Alertes rupture
- /kpi/analyse/valeur-quantite/ - Analyse Pareto
- /kpi/evolution/mensuelle/ - Tendances temporelles
- /kpi/top/items-par-valeur/ - Top items critiques
"""

from datetime import timedelta
from decimal import Decimal
from django.db.models import Count, Sum, F, Q, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from masterdata.models import (
    article, item, categorie, departement, fournisseur,
    emplacement, Personne
)


class TotalAcquisitionValueView(APIView):
    """
    KPI: Valeur totale d'acquisition du patrimoine
    
    Retourne valeur d'acquisition, résiduelle, amortie et taux
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        
        # 1. Valeur d'acquisition (tous les articles)
        acquisition_data = article.objects.filter(
            compte=compte
        ).aggregate(
            total_value=Sum(F('prix_achat') * F('qte')),
            total_articles=Count('id'),
            total_quantity=Sum('qte')
        )
        
        valeur_acquisition = float(acquisition_data['total_value'] or 0)
        
        # 2. Valeur résiduelle actuelle (items actifs)
        items_actifs = item.objects.filter(
            article__compte=compte,
            archive=False
        ).select_related('article', 'article__produit')
        
        valeur_residuelle = sum([
            float(i.calculate_residual_value() or 0)
            for i in items_actifs
        ])
        
        # 3. Calculs dérivés
        valeur_amortie = valeur_acquisition - valeur_residuelle
        taux_amortissement = (valeur_amortie / valeur_acquisition * 100) if valeur_acquisition > 0 else 0
        
        nb_items_actifs = items_actifs.count()
        valeur_moyenne = valeur_residuelle / nb_items_actifs if nb_items_actifs > 0 else 0
        
        return Response({
            "valeur_acquisition": round(valeur_acquisition, 2),
            "valeur_residuelle": round(valeur_residuelle, 2),
            "valeur_amortie": round(valeur_amortie, 2),
            "taux_amortissement": round(taux_amortissement, 2),
            "total_articles": acquisition_data['total_articles'],
            "total_items_actifs": nb_items_actifs,
            "valeur_moyenne_par_item": round(valeur_moyenne, 2)
        })


class ValeurStockVsAffecteeView(APIView):
    """
    KPI: Répartition valeur Stock vs Affectée
    
    Montre le capital dormant vs capital en utilisation
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        
        # 1. Valeur en stock (articles non affectés)
        stock_data = article.objects.filter(
            compte=compte,
            qte_recue__gt=0
        ).aggregate(
            total_value=Sum(F('prix_achat') * F('qte_recue')),
            total_quantity=Sum('qte_recue'),
            total_articles=Count('id')
        )
        
        valeur_stock = float(stock_data['total_value'] or 0)
        qte_stock = stock_data['total_quantity'] or 0
        
        # 2. Valeur affectée (items créés)
        items_affectes = item.objects.filter(
            article__compte=compte,
            archive=False
        ).select_related('article', 'article__produit')
        
        valeur_affectee = sum([
            float(i.calculate_residual_value() or 0)
            for i in items_affectes
        ])
        
        nb_items_affectes = items_affectes.count()
        
        # 3. Calculs globaux
        total_valeur = valeur_stock + valeur_affectee
        taux_affectation = (valeur_affectee / total_valeur * 100) if total_valeur > 0 else 0
        
        return Response({
            "stock": {
                "valeur": round(valeur_stock, 2),
                "quantite": qte_stock,
                "nb_articles": stock_data['total_articles']
            },
            "affecte": {
                "valeur_residuelle": round(valeur_affectee, 2),
                "nb_items": nb_items_affectes
            },
            "global": {
                "valeur_totale": round(total_valeur, 2),
                "taux_affectation": round(taux_affectation, 2),
                "capital_dormant": round(valeur_stock, 2)
            }
        })


class QuantiteGlobaleView(APIView):
    """
    KPI: Vue d'ensemble des quantités
    
    Quantités commandées, reçues, en attente, affectées
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        
        # 1. Quantités d'articles
        articles_stats = article.objects.filter(
            compte=compte
        ).aggregate(
            qte_commandee=Sum('qte'),
            qte_recue=Sum('qte_recue'),
            nb_articles=Count('id')
        )
        
        qte_commandee = articles_stats['qte_commandee'] or 0
        qte_recue = articles_stats['qte_recue'] or 0
        qte_en_attente = qte_commandee - qte_recue
        
        # 2. Quantités d'items
        items_actifs = item.objects.filter(
            article__compte=compte,
            archive=False
        ).count()
        
        items_archives = item.objects.filter(
            article__compte=compte,
            archive=True
        ).count()
        
        # 3. Taux
        taux_reception = (qte_recue / qte_commandee * 100) if qte_commandee > 0 else 100
        taux_affectation = (items_actifs / qte_recue * 100) if qte_recue > 0 else 0
        taux_archivage = (items_archives / (items_actifs + items_archives) * 100) if (items_actifs + items_archives) > 0 else 0
        
        return Response({
            "articles": {
                "quantite_commandee": qte_commandee,
                "quantite_recue": qte_recue,
                "quantite_en_attente": qte_en_attente,
                "taux_reception": round(taux_reception, 2),
                "nb_articles": articles_stats['nb_articles']
            },
            "items": {
                "items_actifs": items_actifs,
                "items_archives": items_archives,
                "total_items": items_actifs + items_archives,
                "taux_affectation": round(taux_affectation, 2),
                "taux_archivage": round(taux_archivage, 2)
            }
        })


class QuantiteParCategorieView(APIView):
    """
    KPI: Répartition des quantités par catégorie
    
    Quantités commandées, reçues, items actifs/archivés par catégorie
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        
        stats = categorie.objects.annotate(
            # Quantités d'articles
            qte_commandee=Sum('produit__article__qte', filter=Q(produit__article__compte=compte)),
            qte_recue=Sum('produit__article__qte_recue', filter=Q(produit__article__compte=compte)),
            nb_articles=Count('produit__article', filter=Q(produit__article__compte=compte), distinct=True),
            
            # Quantités d'items
            nb_items_actifs=Count('produit__article__item', filter=Q(
                produit__article__item__archive=False,
                produit__article__compte=compte
            ), distinct=True),
            nb_items_archives=Count('produit__article__item', filter=Q(
                produit__article__item__archive=True,
                produit__article__compte=compte
            ), distinct=True)
        ).values(
            'libelle',
            'qte_commandee',
            'qte_recue',
            'nb_articles',
            'nb_items_actifs',
            'nb_items_archives'
        ).order_by('-qte_recue')
        
        # Enrichir les données
        result = []
        for cat in stats:
            qte_commandee = cat['qte_commandee'] or 0
            qte_recue = cat['qte_recue'] or 0
            qte_en_attente = qte_commandee - qte_recue
            nb_items_actifs = cat['nb_items_actifs'] or 0
            nb_items_archives = cat['nb_items_archives'] or 0
            total_items = nb_items_actifs + nb_items_archives
            
            taux_reception = (qte_recue / qte_commandee * 100) if qte_commandee > 0 else 100
            taux_affectation = (total_items / qte_recue * 100) if qte_recue > 0 else 0
            
            result.append({
                "categorie": cat['libelle'],
                "quantite_commandee": qte_commandee,
                "quantite_recue": qte_recue,
                "quantite_en_attente": qte_en_attente,
                "taux_reception": round(taux_reception, 2),
                "nb_articles": cat['nb_articles'] or 0,
                "nb_items_actifs": nb_items_actifs,
                "nb_items_archives": nb_items_archives,
                "total_items": total_items,
                "taux_affectation": round(taux_affectation, 2)
            })
        
        return Response(result)


class ValeurParFournisseurView(APIView):
    """
    KPI: Analyse des fournisseurs (valeur et quantité)
    
    Top fournisseurs par valeur, quantité, avec détails complets
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        limit = int(request.GET.get('limit', 20))
        
        # Statistiques par fournisseur
        stats = fournisseur.objects.filter(
            compte=compte
        ).annotate(
            # Quantités
            qte_totale=Sum('article__qte', filter=Q(article__compte=compte)),
            qte_recue=Sum('article__qte_recue', filter=Q(article__compte=compte)),
            nb_articles=Count('article', filter=Q(article__compte=compte)),
            
            # Valeurs
            valeur_acquisition=Sum(
                F('article__prix_achat') * F('article__qte'),
                filter=Q(article__compte=compte)
            ),
            prix_moyen=Avg('article__prix_achat', filter=Q(article__compte=compte)),
            
            # Items créés
            nb_items=Count('article__item', filter=Q(
                article__compte=compte,
                article__item__archive=False
            ))
        ).values(
            'nom',
            'qte_totale',
            'qte_recue',
            'nb_articles',
            'valeur_acquisition',
            'prix_moyen',
            'nb_items'
        ).order_by('-valeur_acquisition')[:limit]
        
        # Calculer valeur résiduelle par fournisseur
        result = []
        for four in stats:
            # Items de ce fournisseur
            items = item.objects.filter(
                article__fournisseur__nom=four['nom'],
                article__compte=compte,
                archive=False
            ).select_related('article', 'article__produit')
            
            valeur_residuelle = sum([
                float(i.calculate_residual_value() or 0)
                for i in items
            ])
            
            valeur_acq = float(four['valeur_acquisition'] or 0)
            valeur_amortie = valeur_acq - valeur_residuelle
            taux_amortissement = (valeur_amortie / valeur_acq * 100) if valeur_acq > 0 else 0
            
            result.append({
                "fournisseur": four['nom'],
                "quantite_commandee": four['qte_totale'] or 0,
                "quantite_recue": four['qte_recue'] or 0,
                "nb_articles": four['nb_articles'] or 0,
                "nb_items": four['nb_items'] or 0,
                "valeur_acquisition": round(valeur_acq, 2),
                "valeur_residuelle": round(valeur_residuelle, 2),
                "valeur_amortie": round(valeur_amortie, 2),
                "taux_amortissement": round(taux_amortissement, 2),
                "prix_moyen": round(float(four['prix_moyen'] or 0), 2)
            })
        
        # Statistiques globales
        total_valeur_acq = sum(f['valeur_acquisition'] for f in result)
        total_valeur_res = sum(f['valeur_residuelle'] for f in result)
        
        return Response({
            "fournisseurs": result,
            "stats_globales": {
                "nb_fournisseurs": len(result),
                "valeur_acquisition_totale": round(total_valeur_acq, 2),
                "valeur_residuelle_totale": round(total_valeur_res, 2)
            }
        })


class StockCritiqueView(APIView):
    """
    KPI: Articles en rupture ou stock faible
    
    Alertes pour la gestion des stocks
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        seuil_stock_faible = int(request.GET.get('seuil', 10))  # 10% par défaut
        
        # 1. Articles en rupture totale (qte_recue = 0)
        rupture = article.objects.filter(
            compte=compte,
            qte_recue=0,
            valider=True
        ).select_related('fournisseur', 'produit', 'produit__categorie').values(
            'id',
            'code_article',
            'designation',
            'qte',
            'fournisseur__nom',
            'produit__categorie__libelle',
            'prix_achat'
        )
        
        # 2. Articles en stock faible (< seuil%)
        stock_faible = article.objects.filter(
            compte=compte,
            qte_recue__gt=0,
            qte__gt=0
        ).annotate(
            taux_stock=(F('qte_recue') * 100.0 / F('qte'))
        ).filter(
            taux_stock__lt=seuil_stock_faible
        ).select_related('fournisseur', 'produit').values(
            'id',
            'code_article',
            'designation',
            'qte',
            'qte_recue',
            'fournisseur__nom',
            'prix_achat'
        ).annotate(
            taux_stock_value=(F('qte_recue') * 100.0 / F('qte'))
        )
        
        # 3. Calcul valeur des articles en rupture
        valeur_bloquee_rupture = sum(
            float(a['prix_achat'] * a['qte']) 
            for a in rupture 
            if a['prix_achat']
        )
        
        return Response({
            "articles_en_rupture": {
                "count": len(rupture),
                "valeur_bloquee": round(valeur_bloquee_rupture, 2),
                "liste": list(rupture)
            },
            "articles_stock_faible": {
                "count": len(stock_faible),
                "seuil": seuil_stock_faible,
                "liste": list(stock_faible)
            }
        })


class QuantiteParDepartementView(APIView):
    """
    KPI: Répartition des quantités par département
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        
        stats = departement.objects.filter(
            compte=compte
        ).annotate(
            nb_items_actifs=Count('item', filter=Q(item__archive=False)),
            nb_items_archives=Count('item', filter=Q(item__archive=True)),
            nb_items_affectes=Count('item', filter=Q(
                item__archive=False,
                item__affectation_personne__isnull=False
            )),
            nb_items_non_affectes=Count('item', filter=Q(
                item__archive=False,
                item__affectation_personne__isnull=True
            ))
        ).values(
            'nom',
            'nb_items_actifs',
            'nb_items_archives',
            'nb_items_affectes',
            'nb_items_non_affectes'
        ).order_by('-nb_items_actifs')
        
        result = []
        for dept in stats:
            total = (dept['nb_items_actifs'] or 0) + (dept['nb_items_archives'] or 0)
            taux_affectation = (dept['nb_items_affectes'] / dept['nb_items_actifs'] * 100) if dept['nb_items_actifs'] > 0 else 0
            
            result.append({
                "departement": dept['nom'],
                "items_actifs": dept['nb_items_actifs'] or 0,
                "items_archives": dept['nb_items_archives'] or 0,
                "total_items": total,
                "items_affectes": dept['nb_items_affectes'] or 0,
                "items_non_affectes": dept['nb_items_non_affectes'] or 0,
                "taux_affectation": round(taux_affectation, 2)
            })
        
        return Response(result)


class AnalyseValeurQuantiteView(APIView):
    """
    KPI: Analyse croisée Valeur × Quantité (Pareto)
    
    Identifie les items représentant 80% de la valeur
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        
        # 1. Prix moyen d'acquisition
        articles = article.objects.filter(compte=compte).aggregate(
            valeur_totale=Sum(F('prix_achat') * F('qte')),
            qte_totale=Sum('qte'),
            prix_moyen_article=Avg('prix_achat')
        )
        
        prix_moyen_unitaire = (
            float(articles['valeur_totale'] or 0) / (articles['qte_totale'] or 1)
        ) if articles['qte_totale'] and articles['qte_totale'] > 0 else 0
        
        # 2. Valeur résiduelle moyenne par item
        items = item.objects.filter(
            article__compte=compte,
            archive=False
        ).select_related('article', 'article__produit')
        
        items_with_value = []
        for i in items:
            valeur = i.calculate_residual_value()
            if valeur:
                items_with_value.append((i, float(valeur)))
        
        valeur_moyenne_item = (
            sum(v for _, v in items_with_value) / len(items_with_value)
        ) if items_with_value else 0
        
        # 3. Analyse Pareto (80/20)
        items_tries = sorted(items_with_value, key=lambda x: x[1], reverse=True)
        
        total_valeur = sum(v for _, v in items_tries)
        valeur_cumul = 0
        nb_items_80_percent = 0
        
        for idx, (item_obj, valeur) in enumerate(items_tries):
            valeur_cumul += valeur
            if valeur_cumul >= total_valeur * 0.8:
                nb_items_80_percent = idx + 1
                break
        
        taux_concentration = (
            nb_items_80_percent / len(items_tries) * 100
        ) if items_tries else 0
        
        return Response({
            "prix_acquisition": {
                "prix_moyen_unitaire": round(prix_moyen_unitaire, 2),
                "prix_moyen_article": round(float(articles['prix_moyen_article'] or 0), 2),
                "valeur_totale_acquisition": round(float(articles['valeur_totale'] or 0), 2),
                "quantite_totale": articles['qte_totale'] or 0
            },
            "valeur_actuelle": {
                "valeur_moyenne_item": round(valeur_moyenne_item, 2),
                "valeur_totale_residuelle": round(total_valeur, 2),
                "nb_items": len(items_tries)
            },
            "analyse_pareto": {
                "nb_items_80_pourcent_valeur": nb_items_80_percent,
                "taux_concentration": round(taux_concentration, 2),
                "interpretation": f"{nb_items_80_percent} items ({taux_concentration:.1f}% du parc) représentent 80% de la valeur"
            }
        })


class EvolutionMensuelleView(APIView):
    """
    KPI: Évolution mensuelle valeur et quantité
    
    Tendances sur 12 mois
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        nb_mois = int(request.GET.get('mois', 12))
        
        # Date de début
        date_debut = timezone.now() - timedelta(days=30*nb_mois)
        
        # 1. Acquisitions par mois
        acquisitions = article.objects.filter(
            compte=compte,
            date_achat__gte=date_debut
        ).annotate(
            mois=TruncMonth('date_achat')
        ).values('mois').annotate(
            qte_commandee=Sum('qte'),
            qte_recue=Sum('qte_recue'),
            nb_articles=Count('id'),
            valeur_acquisition=Sum(F('prix_achat') * F('qte'))
        ).order_by('mois')
        
        # 2. Affectations par mois
        affectations = item.objects.filter(
            article__compte=compte,
            date_affectation__gte=date_debut
        ).annotate(
            mois=TruncMonth('date_affectation')
        ).values('mois').annotate(
            nb_items_crees=Count('id')
        ).order_by('mois')
        
        # 3. Archivages par mois
        archivages = item.objects.filter(
            article__compte=compte,
            archive=True,
            date_archive__gte=date_debut,
            date_archive__isnull=False
        ).annotate(
            mois=TruncMonth('date_archive')
        ).values('mois').annotate(
            nb_items_archives=Count('id')
        ).order_by('mois')
        
        return Response({
            "periode": {
                "debut": date_debut.strftime('%Y-%m-%d'),
                "fin": timezone.now().strftime('%Y-%m-%d'),
                "nb_mois": nb_mois
            },
            "acquisitions_par_mois": list(acquisitions),
            "affectations_par_mois": list(affectations),
            "archivages_par_mois": list(archivages)
        })


class TopItemsParValeurView(APIView):
    """
    KPI: Top N items par valeur résiduelle
    
    Identifie les actifs les plus critiques
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        limit = int(request.GET.get('limit', 10))
        
        # Récupérer items actifs
        items = item.objects.filter(
            article__compte=compte,
            archive=False
        ).select_related(
            'article',
            'article__produit',
            'article__produit__categorie',
            'article__fournisseur',
            'departement',
            'emplacement',
            'affectation_personne'
        )
        
        # Calculer valeur pour chaque item
        items_with_value = []
        for i in items:
            valeur = i.calculate_residual_value()
            if valeur and valeur > 0:
                items_with_value.append({
                    "id": i.id,
                    "reference": i.reference_auto,
                    "designation": i.article.designation if i.article else None,
                    "code_article": i.article.code_article if i.article else None,
                    "categorie": i.article.produit.categorie.libelle if i.article and i.article.produit and i.article.produit.categorie else None,
                    "fournisseur": i.article.fournisseur.nom if i.article and i.article.fournisseur else None,
                    "departement": i.departement.nom if i.departement else None,
                    "emplacement": i.emplacement.nom if i.emplacement else None,
                    "affectation": f"{i.affectation_personne.nom} {i.affectation_personne.prenom}" if i.affectation_personne else "Non affecté",
                    "valeur_residuelle": round(float(valeur), 2),
                    "prix_achat": float(i.article.prix_achat) if i.article else 0,
                    "date_achat": i.article.date_achat.strftime('%Y-%m-%d') if i.article and i.article.date_achat else None
                })
        
        # Trier par valeur DESC
        items_with_value.sort(key=lambda x: x['valeur_residuelle'], reverse=True)
        
        # Top N
        top_items = items_with_value[:limit]
        
        # Statistiques
        total_valeur_top = sum(i['valeur_residuelle'] for i in top_items)
        total_valeur_global = sum(i['valeur_residuelle'] for i in items_with_value)
        concentration = (total_valeur_top / total_valeur_global * 100) if total_valeur_global > 0 else 0
        
        return Response({
            "top_items": top_items,
            "stats": {
                "nb_total_items": len(items_with_value),
                "valeur_top_n": round(total_valeur_top, 2),
                "valeur_globale": round(total_valeur_global, 2),
                "concentration": round(concentration, 2),
                "interpretation": f"Les {limit} items les plus chers représentent {concentration:.1f}% de la valeur totale"
            }
        })


class ValeurParCategorieDetailView(APIView):
    """
    KPI: Analyse détaillée valeur par catégorie
    
    Valeur acquisition, résiduelle, amortie par catégorie
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        
        # Récupérer toutes les catégories
        categories = categorie.objects.all()
        
        result = []
        for cat in categories:
            # Articles de cette catégorie
            articles_cat = article.objects.filter(
                compte=compte,
                produit__categorie=cat
            ).aggregate(
                valeur_acquisition=Sum(F('prix_achat') * F('qte')),
                qte_totale=Sum('qte'),
                qte_recue=Sum('qte_recue'),
                nb_articles=Count('id')
            )
            
            # Items de cette catégorie
            items_cat = item.objects.filter(
                article__compte=compte,
                article__produit__categorie=cat,
                archive=False
            ).select_related('article', 'article__produit')
            
            valeur_residuelle = sum([
                float(i.calculate_residual_value() or 0)
                for i in items_cat
            ])
            
            valeur_acq = float(articles_cat['valeur_acquisition'] or 0)
            valeur_amortie = valeur_acq - valeur_residuelle
            taux_amortissement = (valeur_amortie / valeur_acq * 100) if valeur_acq > 0 else 0
            
            if articles_cat['nb_articles'] and articles_cat['nb_articles'] > 0:
                result.append({
                    "categorie": cat.libelle,
                    "quantite_commandee": articles_cat['qte_totale'] or 0,
                    "quantite_recue": articles_cat['qte_recue'] or 0,
                    "nb_articles": articles_cat['nb_articles'],
                    "nb_items": items_cat.count(),
                    "valeur_acquisition": round(valeur_acq, 2),
                    "valeur_residuelle": round(valeur_residuelle, 2),
                    "valeur_amortie": round(valeur_amortie, 2),
                    "taux_amortissement": round(taux_amortissement, 2)
                })
        
        # Trier par valeur résiduelle DESC
        result.sort(key=lambda x: x['valeur_residuelle'], reverse=True)
        
        # Stats globales
        total_valeur_acq = sum(c['valeur_acquisition'] for c in result)
        total_valeur_res = sum(c['valeur_residuelle'] for c in result)
        
        return Response({
            "categories": result,
            "stats_globales": {
                "nb_categories": len(result),
                "valeur_acquisition_totale": round(total_valeur_acq, 2),
                "valeur_residuelle_totale": round(total_valeur_res, 2),
                "valeur_amortie_totale": round(total_valeur_acq - total_valeur_res, 2)
            }
        })


class DashboardValeurQuantiteView(APIView):
    """
    KPI: Dashboard complet Valeur & Quantité
    
    Vue unique avec tous les KPIs principaux
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        compte = request.user.compte
        
        # 1. Valeurs globales
        articles_data = article.objects.filter(compte=compte).aggregate(
            valeur_acquisition=Sum(F('prix_achat') * F('qte')),
            qte_commandee=Sum('qte'),
            qte_recue=Sum('qte_recue')
        )
        
        items_actifs = item.objects.filter(
            article__compte=compte,
            archive=False
        ).select_related('article', 'article__produit')
        
        valeur_residuelle = sum([
            float(i.calculate_residual_value() or 0)
            for i in items_actifs
        ])
        
        valeur_acq = float(articles_data['valeur_acquisition'] or 0)
        valeur_amortie = valeur_acq - valeur_residuelle
        
        # 2. Quantités
        nb_items_actifs = items_actifs.count()
        nb_items_archives = item.objects.filter(
            article__compte=compte,
            archive=True
        ).count()
        
        return Response({
            "valeur": {
                "acquisition": round(valeur_acq, 2),
                "residuelle": round(valeur_residuelle, 2),
                "amortie": round(valeur_amortie, 2),
                "taux_amortissement": round(valeur_amortie/valeur_acq*100, 2) if valeur_acq > 0 else 0
            },
            "quantite": {
                "commandee": articles_data['qte_commandee'] or 0,
                "recue": articles_data['qte_recue'] or 0,
                "en_attente": (articles_data['qte_commandee'] or 0) - (articles_data['qte_recue'] or 0),
                "items_actifs": nb_items_actifs,
                "items_archives": nb_items_archives
            },
            "moyennes": {
                "prix_moyen_unitaire": round(valeur_acq/(articles_data['qte_commandee'] or 1), 2),
                "valeur_moyenne_item": round(valeur_residuelle/nb_items_actifs, 2) if nb_items_actifs > 0 else 0
            }
        })
# ```

# **Endpoint** : `GET /kpi/dashboard/valeur-quantite/`

# **Réponse Complète** :
# ```json
# {
#   "valeur": {
#     "acquisition": 2500000.00,
#     "residuelle": 1850000.00,
#     "amortie": 650000.00,
#     "taux_amortissement": 26.00
#   },
#   "quantite": {
#     "commandee": 1500,
#     "recue": 1450,
#     "en_attente": 50,
#     "items_actifs": 1379,
#     "items_archives": 89
#   },
#   "moyennes": {
#     "prix_moyen_unitaire": 1666.67,
#     "valeur_moyenne_item": 1341.43
#   }
# }
# ```

# ---

# ## 📋 Récapitulatif des Endpoints à Ajouter

# ```python
# # masterdata/urls.py - AJOUTER

# from masterdata.Views.ValeurQuantiteKPI import (
#     TotalAcquisitionValueView,
#     ValeurStockVsAffecteeView,
#     QuantiteGlobaleView,
#     QuantiteParCategorieView,
#     QuantiteParDepartementView,
#     ValeurParFournisseurView,
#     StockCritiqueView,
#     AnalyseValeurQuantiteView,
#     EvolutionMensuelleView,
#     TopItemsParValeurView,
#     ValeurParCategorieDetailView,
#     DashboardValeurQuantiteView
# )

# urlpatterns += [
#     # KPIs Valeur
#     path('kpi/valeur/acquisition/', TotalAcquisitionValueView.as_view(), name='kpi-valeur-acquisition'),
#     path('kpi/valeur/stock-vs-affectee/', ValeurStockVsAffecteeView.as_view(), name='kpi-stock-affectee'),
#     path('kpi/valeur/par-fournisseur/', ValeurParFournisseurView.as_view(), name='kpi-valeur-fournisseur'),
#     path('kpi/valeur/par-categorie-detail/', ValeurParCategorieDetailView.as_view(), name='kpi-valeur-categorie'),
    
#     # KPIs Quantité
#     path('kpi/quantite/globale/', QuantiteGlobaleView.as_view(), name='kpi-quantite-globale'),
#     path('kpi/quantite/par-categorie/', QuantiteParCategorieView.as_view(), name='kpi-quantite-categorie'),
#     path('kpi/quantite/par-departement/', QuantiteParDepartementView.as_view(), name='kpi-quantite-departement'),
#     path('kpi/stock/critique/', StockCritiqueView.as_view(), name='kpi-stock-critique'),
    
#     # KPIs Analyse
#     path('kpi/analyse/valeur-quantite/', AnalyseValeurQuantiteView.as_view(), name='kpi-analyse'),
#     path('kpi/evolution/mensuelle/', EvolutionMensuelleView.as_view(), name='kpi-evolution'),
#     path('kpi/top/items-par-valeur/', TopItemsParValeurView.as_view(), name='kpi-top-items'),
    
#     # Dashboard complet
#     path('kpi/dashboard/valeur-quantite/', DashboardValeurQuantiteView.as_view(), name='kpi-dashboard'),
# ]
# ```

# ---

# **✅ Fichier créé** : `masterdata/Views/ValeurQuantiteKPI.py`  
# **✅ 10 vues KPIs** prêtes à utiliser  
# **✅ Documentation** : `KPIs_VALEUR_QUANTITE.md`

# **Prochaine étape** : Ajouter les endpoints dans `urls.py` ! 🚀

