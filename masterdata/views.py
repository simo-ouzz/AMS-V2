from django_filters import rest_framework as django_filters
from django.views import View
from masterdata.config.CustomPageNumberPagination import CustomPageNumberPagination
from masterdata.config.ArticleFiltrage import ArticleFilter
from masterdata.config.InventaireFilterage import InventaireFilter
from masterdata.config.ItemFilterage import ItemFilter
from masterdata.serializers import *
from masterdata.models import *
from masterdata.services.items import (
    ArchiveItemsImportError,
    archive_or_unarchive_item_service,
    archive_items_batch_service,
    import_archive_items_from_excel_service,
    list_archive_items_for_user,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.http import HttpResponse

from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from .models import article
from rest_framework import filters
from datatables.mixins import ServerSideDataTableView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Permission


from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
from django.contrib import admin


class UserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # This is the user associated with the token
        user_data = {
            "id": user.id,
            "nom": user.nom,
            "prenom": user.prenom,
            "email": user.email,
        }
        return Response(user_data, status=200)


class LoginUserView(APIView):
    def post(self, request):
        data = request.data
        email = data.get("email")
        password = data.get("password")

        try:
            user = UserWeb.objects.get(email=email)
            if user.check_password(password, user.password):
                return Response(
                    {"email": user.email, "username": f"{user.nom} {user.prenom}"}
                )

            else:
                return Response(
                    {"status": "failed", "msg": "invalid username or password"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except UserWeb.DoesNotExist:
            return Response(
                {"status": "failed", "msg": "invalid username or password"},
                status=status.HTTP_400_BAD_REQUEST,
            )


from django.contrib.auth.decorators import login_required


@login_required
def assign_groups_view(request):
    users = UserWeb.objects.all()
    groups = Group.objects.all()

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        group_ids = request.POST.getlist("group_ids")
        try:
            user = UserWeb.objects.get(id=user_id)
            selected_groups = Group.objects.filter(id__in=group_ids)
            user.groups.set(selected_groups)
            messages.success(
                request,
                f"Les groupes ont été mis à jour pour l'utilisateur {user.email}.",
            )
        except UserWeb.DoesNotExist:
            messages.error(request, "Utilisateur non trouvé.")
        return redirect("assign-groups")

    context = {
        "title": "Affecter les utilisateurs aux groupes",
        "users": users,
        "groups": groups,
    }
    return render(request, "admin/assign_groups.html", context)


class departementsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.compte:
            departements = departement.objects.filter(compte=user.compte)
            serializer = DepartementSerializer(departements, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class emplacementsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.compte:
            emplacements = emplacement.objects.filter(
                zone__location__compte=user.compte
            )
            serializer = EmplacementSerializer(emplacements, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


from django.db.models import Count


class LocationsMobileListAPIView(APIView):
    def get(self, request):
        locations = location.objects.all()
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ZonesMobileListAPIView(APIView):
    def get(self, request, id):
        zones = zone.objects.filter(location=id)
        serializer = zonesListFilterAPIView(zones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EmplacementsMobileListAPIView(APIView):
    def get(self, request, id):
        emplacements = emplacement.objects.filter(zone=id)
        serializer = EmplacementSerializer(emplacements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ArticlesListAPIView(ServerSideDataTableView):
    """
    API ultra-simplifiée pour les articles avec support DataTable automatique.
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    - Export Excel/CSV (activé par défaut)
    """
    model = article
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]
    # filterset_class = ArticleFilter
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'articles'
    
    # Configuration DataTable simple
    search_fields = [
        'code_article',
        'designation',
        'fournisseur__nom',
        'produit__libelle',
        'produit__categorie__libelle',
        'N_facture'
    ]
    
    order_fields = [
        'id',
        'code_article',
        'designation',
        'date_achat',
        'prix_achat',
        'fournisseur__nom',
        'qte_recue',
        'created_at'
    ]
    
    # Mapping des filtres frontend -> backend (automatique via @datatables/)
    filter_aliases = {
        'id': 'id',
        'code_article': 'code_article',
        'designation': 'designation',
        'categorie': 'produit__categorie__libelle',
        'date_achat': 'date_achat',
        'fournisseur': 'fournisseur__nom',
        'date_reception': 'date_reception',
        'qte': 'qte',
        'qte_recue': 'qte_recue',
        'N_facture': 'N_facture',
        'prix_achat': 'prix_achat'
    }
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100

    def get_datatable_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les articles valides avec quantité > 0 sont retournés.
        """
        if not self.request.user.compte:
            return article.objects.none()
            
        return article.objects.filter(
            compte=self.request.user.compte,
            qte_recue__gt=0,
            valider=True
        ).select_related(
            'produit',
            'produit__categorie',
            'fournisseur',
            'marque'
        ).prefetch_related(
            'item_set'
        )


class produitsListAPIView(APIView):
    def get(self, request):
        produits = produit.objects.all()
        serializer = ProduitSerializer(produits, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class fournisseursListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.compte:
            fournisseurs = fournisseur.objects.filter(compte=user.compte)
            serializer = FournisseurSerializer(fournisseurs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class naturesListAPIView(APIView):
    def get(self, request):
        natures = nature.objects.all()
        serializer = NatureSerializer(natures, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoriesListAPIView(APIView):
    def get(self, request):
        categories = categorie.objects.all()
        serializer = CategorieSerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class marquesListAPIView(APIView):
    def get(self, request):
        marques = marque.objects.all()
        serializer = MarqueSerializer(marques, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class tagsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.compte:
            tags = tag.objects.filter(compte=user.compte)
            serializer = TagSerializer(tags, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TypeTagsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        type_tags = type_tag.objects.all()
        serializer = TypeTagSerializer(type_tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InventaireEmplacementListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les inventaires d'emplacement avec support DataTable
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    """
    model = inventaire
    serializer_class = InventaireSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'inventaires_emplacement'
    
    filterset_class = InventaireFilter
    
    # Configuration DataTable
    search_fields = [
        'nom',
        'reference', 
        'inventaire_emplacement_set__emplacement__nom',
        'user__username',
        'created_at',
        'departement__nom'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'nom',
        'reference',
        'created_at',
        'inventaire_emplacement_set__emplacement__nom',
        'departement__nom'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'nom': 'nom',
        'reference': 'reference',
        'emplacement': 'inventaire_emplacement_set__emplacement__nom',
        'emplacement_nom': 'inventaire_emplacement_set__emplacement__nom',
        'user': 'user__username',
        'user_nom': 'user__first_name',
        'user_prenom': 'user__last_name',
        'date_creation': 'created_at',
        'statut': 'statut',
        'categorie': 'categorie',
        'departement': 'departement__nom'
    }
    
    # Configuration des colonnes composées
    composite_columns = {
        'user_full_name': {
            'type': 'concat',
            'fields': ['user__first_name', 'user__last_name'],
            'separator': ' '
        },
        'inventaire_full_info': {
            'type': 'concat',
            'fields': ['nom', 'reference'],
            'separator': ' - '
        }
    }

    def get_datatable_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les inventaires d'emplacement valides sont retournés.
        """
        if not self.request.user.compte:
            return inventaire.objects.none()
        
        return inventaire.objects.filter(
            user__compte=self.request.user.compte, 
            categorie="Emplacement"
        ).select_related(
            'user',
            'departement'
        ).prefetch_related(
            'inventaire_emplacement_set',
            'inventaire_emplacement_set__emplacement'
        ).order_by("-id")

    def filter_queryset(self, queryset):
        filtered_queryset = super().filter_queryset(queryset)
        return filtered_queryset

    # DataTable s'occupe de la sérialisation et de la pagination avec InventaireSerializer


class InventaireEmplacementListMobileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            if not user.compte:
                return Response(
                    {"error": "User does not have an associated account"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            inventaires = inventaire.objects.filter(user__compte=user.compte)

            serialized_data = []
            for inv in inventaires:
                emplacements = (
                    inventaire_emplacement.objects.filter(
                        inventaire_id=inv.id, start_at=True
                    )
                    .exclude(statut="Terminer")
                    .distinct()
                )
                user_instance = get_object_or_404(UserWeb, pk=inv.user.id)
                user_full_name = f"{user_instance.nom} {user_instance.prenom}"

                for emp in emplacements:
                    serialized_data.append(
                        {
                            "id": emp.id,
                            "inventaireId": inv.id,
                            "categorie": inv.categorie,
                            "affceted_at": (
                                emp.affceted_at.id if emp.affceted_at else None
                            ),  # Extraire l'ID ou d'autres champs nécessaires
                            "emplacementId": emp.emplacement.id,
                            "operateur": (
                                emp.affceted_at.nom + " " + emp.affceted_at.prenom
                                if emp.affceted_at
                                else None
                            ),
                            "nom": inv.nom,
                            "reference": inv.reference,
                            "emplacement_nom": emp.emplacement.nom,
                            "user": user_full_name,  # Le nom complet de l'utilisateur
                            "created_at": emp.created_at,
                            "statut": emp.statut,
                        }
                    )

            return Response(serialized_data, status=status.HTTP_200_OK)

        except inventaire.DoesNotExist:
            return Response(
                {"error": "Inventaire not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except UserWeb.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from openpyxl import Workbook


from datatables import DataTableListView, DataTableConfig, CompositeDataTableFilter, DjangoFilterDataTableFilter, DateRangeFilter, StatusFilter

class ItemListAPIView(ServerSideDataTableView):
    """
    API ultra-simplifiée pour les items avec support DataTable automatique.
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    - Export Excel/CSV (activé par défaut)
    """
    model = item
    serializer_class = ItemsSerializer
    permission_classes = [IsAuthenticated]
    # filterset_class = ItemFilter
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'items'
    
    # Configuration DataTable simple
    search_fields = [
        'reference_auto',
        'numero_serie', 
        'article__designation',
        'article__code_article',
        'emplacement__nom',
        'departement__nom',
        'affectation_personne__nom',
        'affectation_personne__prenom'
    ]
    
    order_fields = [
        'id',
        'reference_auto',
        'article__designation',
        'emplacement__nom',
        'departement__nom',
        'statut',
        'created_at',
        'date_affectation'
    ]
    
    # Mapping des filtres frontend -> backend (automatique via @datatables/)
    filter_aliases = {
        'id': 'id',
        'reference_auto': 'reference_auto',
        'numero_serie': 'numero_serie',
        'article__designation': 'article__designation',  # Support direct du nom de champ
        'article__code_article': 'article__code_article',
        'article__prix_achat': 'article__prix_achat',
        'article__fournisseur': 'article__fournisseur__nom',
        'article__categorie': 'article__produit__categorie__libelle',  # Support pour catégorie
        'article__produit': 'article__produit__libelle',  # Support pour produit/famille
        'article__marque': 'article__marque__nom',  # Support pour marque
        'article__nature': 'article__nature__libelle',  # Support pour nature
        'fournisseur': 'article__fournisseur__nom',  # Alias court pour fournisseur
        'emplacement': 'emplacement__nom',
        'departement': 'departement__nom',
        'statut': 'statut',
        'created_at': 'created_at',
        'date_affectation': 'date_affectation',
        'article_date_achat': 'article__date_achat',
        'article_n_facture': 'article__N_facture',
        # 'affectation_personne_full_name': 'affectation_personne__nom',  # Géré par composite_columns
        'zone': 'emplacement__zone__nom',
        'location': 'emplacement__zone__location__nom',  # Alias pour location
        'valeur_residuelle': 'valeur_residuelle',
        'article_designation': 'article__designation',  # Alias alternatif
        'article_code': 'article__code_article'  # Alias alternatif
    }
    
    # Configuration des colonnes composées
    composite_columns = {
        'affectation_personne_full_name': {
            'type': 'concat',
            'fields': ['affectation_personne__nom', 'affectation_personne__prenom'],
            'separator': ' '
        },
        'article_full_name': {
            'type': 'concat', 
            'fields': ['article__designation', 'article__code_article'],
            'separator': ' - '
        }
    }
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100

    def get_datatable_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les items valides non archivés sont retournés.
        """
        if not self.request.user.compte:
            return item.objects.none()
            
        return item.objects.filter(
            article__compte=self.request.user.compte, 
            archive=False
        ).select_related(
            'article',
            'article__produit',
            'article__produit__categorie',
            'article__fournisseur',
            'article__marque',
            'emplacement',
            'emplacement__zone',
            'emplacement__zone__location',
            'departement',
            'affectation_personne',
            'tag'
        ).prefetch_related(
            'archive_items'
        )


class EditItemAPIView(APIView):
    def get(self, request, item_id):
        try:
            item_obj = item.objects.get(
                id=item_id
            )  # Utilise 'Article' avec une majuscule
        except item.DoesNotExist:
            return Response(
                {"message": "item not found"}, status=status.HTTP_404_NOT_FOUND
            )
        """Gère les requêtes DataTable avec filtres avancés"""
        try:
            from datatables import (
                DataTableProcessor, DataTableConfig, 
                CompositeDataTableFilter, DjangoFilterDataTableFilter,
                DataTableSerializer
            )
            from datatables.filters import StringFilter, DateFilter, NumberFilter
            
            # Configuration DataTable
            config = DataTableConfig(
                search_fields=self.search_fields,
                order_fields=self.order_fields,
                default_order=self.default_order,
                page_size=self.page_size,
                min_page_size=self.min_page_size,
                max_page_size=self.max_page_size
            )
            
            # Queryset de base
            queryset = self.get_datatable_queryset()
            
            # Filtres avancés composites
            composite_filter = CompositeDataTableFilter()
            
            # 1. Filtre Django Filter classique
            composite_filter.add_filter(DjangoFilterDataTableFilter(ItemFilter))
            
            # 2. Filtres avancés par type de champ
            
            # Filtres de chaînes avec tous les opérateurs
            string_filter = StringFilter([
                'reference_auto',
                'article__designation',
                'article__code_article',
                'emplacement__nom',
                'departement__nom',
                'affectation_personne__nom',
                'affectation_personne__prenom',
                'statut'
            ])
            composite_filter.add_filter(string_filter)
            
            # Filtres de dates avec tous les opérateurs
            date_filter = DateFilter([
                'created_at',
                'date_affectation',
                'article__date_achat',
                'article__date_reception'
            ])
            composite_filter.add_filter(date_filter)
            
            # Filtres numériques avec tous les opérateurs
            number_filter = NumberFilter([
                'id',
                'article__prix_achat',
                'article__qte'
            ])
            composite_filter.add_filter(number_filter)
            
            # Processeur DataTable avec filtres composites
            processor = DataTableProcessor(
                config=config,
                filter_handler=composite_filter,
                serializer_handler=DataTableSerializer(ItemsSerializer)
            )
            
            return processor.process(request, queryset)
            
        except Exception as e:
            # Fallback vers REST API en cas d'erreur DataTable
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erreur DataTable, fallback vers REST: {str(e)}")
            return self.handle_rest_request(request)
    

        wb = Workbook()
        ws = wb.active
        ws.title = "Items"

        # En-têtes des colonnes
        headers = [
            "ID",
            "Code Article",
            "Famille",
            "Catégorie",
            "Prix d'Achat",
            "Date d'Achat",
            "Numéro Facture",
            "Date d'Affectation",
            "Emplacement",
            "Zone",
            "Département",
            "Désignation",
            "Fournisseur",
            "Tag",
            "Affectation Personne",
            "Archive",
            "Valeur Résiduelle",
            "Commentaire",
        ]
        ws.append(headers)

        # Remplir les lignes avec les données extraites
        for item_obj in queryset:
            item_data = ItemsSerializer(item_obj).data
            item_data["valeur_residuelle"] = item_obj.calculate_residual_value()
            print(item_data)
            row = [
                item_data["id"],
                item_data.get("article", {}).get("code_article", None),
                item_data.get("article", {}).get("produit", None),
                item_data.get("produit_categorie", None),
                item_data.get("article", {}).get("prix_achat", None),
                item_data.get("article", {}).get("date_achat", None),
                item_data.get("article", {}).get("N_facture", None),
                (
                    item_data.get("date_affectation", "").strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(item_data.get("date_affectation"), datetime)
                    else item_data.get("date_affectation", "")
                ),
                item_data.get("emplacement", ""),
                item_data.get("zone", ""),
                item_data.get("departement", ""),
                item_data.get("article", {}).get("designation", None),
                item_data.get("article", {}).get("fournisseur", ""),
                item_data.get("tag", ""),
                item_data.get("affectation_personne_full_name", ""),
                item_data.get("archive", ""),
                item_data.get("valeur_residuelle", ""),
                item_data.get("commentaire", ""),
            ]
            ws.append(row)

        # Retourner la réponse HTTP pour télécharger le fichier Excel
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="items.xlsx"'

        wb.save(response)
        return response

    def format_date(self, date_value):
        if isinstance(date_value, datetime):
            return date_value.strftime("%Y-%m-%d %H:%M:%S")
        return date_value


class EditItemAPIView(APIView):
    def get(self, request, item_id):
        try:
            item_obj = item.objects.get(
                id=item_id
            )  # Utilise 'Article' avec une majuscule
        except item.DoesNotExist:
            return Response(
                {"message": "item not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = EditItemSerializer(
            item_obj, context={"request": request}
        )  # Passe le contexte
        return Response(serializer.data)


class ItemUpdateAPIView(APIView):
    def put(self, request, item_id, format=None):
        try:
            item_obj = get_object_or_404(article, id=item_id)
        except article.DoesNotExist:
            return Response(
                {"message": "Item not found"}, status=status.HTTP_404_NOT_FOUND
            )

        print("Données reçues :", request.data)  # Debug pour voir les données envoyées

        serializer = UpdateItemArticleSerializer(
            item_obj, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Modification réussie", "data": serializer.data},
                status=status.HTTP_200_OK,
            )

        print("Erreurs de validation:", serializer.errors)
        return Response(
            {"message": "Erreur de validation", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ArchiveItemListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les items archivés avec support DataTable
    
    Fonctionnalités:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés
    - Export Excel
    """
    model = item
    serializer_class = ItemsSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'items_archives'
    
    filterset_class = ItemFilter
    
    # Configuration DataTable
    search_fields = [
        'id',
        'reference_auto',
        'numero_serie',
        'article__code_article',
        'departement__nom',
        'article__designation',
        'affectation_personne__prenom',
        'affectation_personne__nom',
        'emplacement__nom',
        'article__fournisseur__nom',
        'article__numero_comptable',
        'article__N_facture',
        'article__produit__libelle',
        'article__produit__categorie__libelle'
    ]
    
    ordering_fields = [
        'id',
        'reference_auto',
        'article__code_article',
        'departement__nom',
        'article__designation',
        'affectation_personne__nom',
        'emplacement__nom',
        'article__date_achat',
        'article__produit__categorie__libelle',
        'article__fournisseur__nom',
        'article__prix_achat',
        'article__N_facture',
        'article__produit__libelle'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'reference_auto': 'reference_auto',
        'numero_serie': 'numero_serie',
        'article_designation': 'article__designation',
        'article_code_article': 'article__code_article',
        'emplacement': 'emplacement__nom',
        'departement': 'departement__nom',
        'statut': 'statut',
        'created_at': 'created_at',
        'date_affectation': 'date_affectation',
        'article_prix_achat': 'article__prix_achat',
        'article_N_facture': 'article__N_facture'
    }
    
    # Colonnes composées
    composite_columns = {
        'affectation_personne_full_name': {
            'type': 'concat',
            'fields': ['affectation_personne__nom', 'affectation_personne__prenom'],
            'separator': ' '
        }
    }

    def get_datatable_queryset(self):
        """Queryset de base - items archivés uniquement"""
        if not self.request.user.compte:
            return item.objects.none()
            
        return item.objects.filter(
            article__compte=self.request.user.compte,
            archive=True
        ).select_related(
            'article',
            'article__produit',
            'article__produit__categorie',
            'article__fournisseur',
            'article__marque',
            'emplacement',
            'emplacement__zone',
            'departement',
            'affectation_personne',
            'tag'
        ).prefetch_related(
            'archive_items'
        ).order_by("-id")



class MobileArticleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Récupérer tous les articles sans filtrage
        compte = request.user.compte
        queryset = article.objects.filter(compte=compte, qte_recue__gt=0, valider=True)

        # Sérialisation
        serializer = ArticleSerializeres(queryset, many=True)

        # Retourner directement les données sérialisées
        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework.parsers import MultiPartParser, FormParser


class ArticleCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        data = request.data
        print(data)

        serializer = CreateOneArticleSerializer(data=data)

        if serializer.is_valid():
            # Affecter l'utilisateur authentifié
            article_instance = serializer.save(compte=request.user.compte)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EditArticleAPIView(APIView):
    def get(self, request, article_id):
        try:
            article_obj = article.objects.get(
                id=article_id
            )  # Utilise 'Article' avec une majuscule
        except article.DoesNotExist:
            return Response(
                {"message": "Article not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = EditArticleSerializer(
            article_obj, context={"request": request}
        )  # Passe le contexte
        return Response(serializer.data)


class ArticleUpdateAPIView(APIView):
    def put(self, request, article_id, Format=None):
        print(request.data)
        try:
            article_obj = article.objects.get(id=article_id)
        except article.DoesNotExist:
            return Response(
                {"message": "Article not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CreateOneArticleSerializer(article_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ArticleDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id_article, format=None):
        try:
            # Récupérer l'article par son ID (pk)
            article_instance = article.objects.get(pk=id_article)

            # Vérifier si qte est égale à qte_recue
            if article_instance.qte == article_instance.qte_recue:
                # Si oui, supprimer l'article
                article_instance.delete()
                return Response(
                    {"message": "Article deleted successfully"},
                    status=status.HTTP_200_OK,
                )
            else:
                # Si non, renvoyer un message d'erreur
                return Response(
                    {
                        "error": "Cannot delete article. Quantity received is not equal to the original quantity."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except article.DoesNotExist:
            # Si l'article n'existe pas, renvoyer une erreur 404
            return Response(
                {"error": "Article not found"}, status=status.HTTP_404_NOT_FOUND
            )


class ArticleImportAPIView(APIView):

    REQUIRED_COLUMNS = [
        "famille",
        "N facture",
        "designation",
        "date achat",
        "prix achat",
    ]

    def post(self, request, *args, **kwargs):
        excel_file = request.FILES.get("file")
        if not excel_file:
            return Response(
                "Veuillez fournir un fichier Excel.", status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Étape 1 : Lire le fichier Excel
            df = pd.read_excel(excel_file)
        except Exception as e:
            return Response(
                f"Erreur de lecture du fichier Excel: {str(e)}",
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Étape 2 : Convertir les données en dictionnaire
        data = df.to_dict(orient="records")

        # Étape 3 : Validation des données
        errors = self.validate_data(data)

        if errors:
            errors_str = "\n".join(errors).encode("utf-8")
            return Response(errors_str, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Étape 4 : Ajouter les articles si les données sont valides
            valid_articles = self.add_articles(data, request.user)
        except Exception as e:
            return Response(
                f"Erreur lors de l'ajout des articles: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            # Étape 5 : Enregistrer les informations du fichier après succès
            fichier = self.enregistrer_fichier(excel_file, len(df))
        except Exception as e:
            return Response(
                f"Erreur lors de l'enregistrement des informations du fichier: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Données importées avec succès."},
            status=status.HTTP_201_CREATED,
        )

    def enregistrer_fichier(self, excel_file, nombre_lignes):
        nom_fichier = excel_file.name
        taille_fichier = excel_file.size

        fichier_existant = Fichier.objects.filter(nom=nom_fichier).first()
        if (
            fichier_existant
            and fichier_existant.taille == taille_fichier
            and fichier_existant.nombre_lignes == nombre_lignes
        ):
            raise Exception(f"Le fichier '{nom_fichier}' a déjà été importé.")

        return Fichier.objects.create(
            nom=nom_fichier, taille=taille_fichier, nombre_lignes=nombre_lignes
        )

    def validate_data(self, data):
        errors = []
        for row_index, row in enumerate(data):
            row_errors = self.validate_row(row, row_index)
            if row_errors:
                errors.extend(row_errors)
        return errors

    def validate_row(self, row, row_index):
        row_errors = []

        # Vérification des colonnes manquantes
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in row]
        if missing_columns:
            row_errors.append(
                f"Ligne {row_index + 1}: Colonnes manquantes: {'| '.join(missing_columns)}."
            )

        # Vérification des colonnes vides
        empty_columns = [
            col for col in self.REQUIRED_COLUMNS if col in row and pd.isna(row[col])
        ]
        if empty_columns:
            row_errors.append(
                f"Ligne {row_index + 1}: Colonnes vides: {'| '.join(empty_columns)}."
            )

        # Validation des clés étrangères
        self.validate_foreign_keys(row, row_index, row_errors)

        return row_errors

    def validate_foreign_keys(self, row, row_index, row_errors):
        self.get_foreign_key_instance(
            produit, row.get("famille"), "libelle", row_index, "famille", row_errors
        )
        self.get_foreign_key_instance(
            marque, row.get("marque"), "nom", row_index, "marque", row_errors
        )
        self.get_foreign_key_instance(
            fournisseur,
            row.get("fournisseur"),
            "nom",
            row_index,
            "fournisseur",
            row_errors,
        )
        self.get_foreign_key_instance(
            nature, row.get("nature"), "libelle", row_index, "nature", row_errors
        )

    def get_foreign_key_instance(
        self, model, value, lookup_field, row_index, field_name, row_errors
    ):
        if pd.isna(value):
            return None

        try:
            return model.objects.get(
                **{lookup_field: value}
            )  # Assure une instance unique
        except model.DoesNotExist:
            row_errors.append(
                f"Ligne {row_index + 1}: {field_name} '{value}' non trouvé."
            )
        except model.MultipleObjectsReturned:
            row_errors.append(
                f"Ligne {row_index + 1}: {field_name} '{value}' correspond à plusieurs enregistrements."
            )
        return None

    def add_articles(self, data, user):
        valid_articles = []
        for row_index, row in enumerate(data):
            try:
                article_data = self.construct_article_data(row, user)

                # Créer l'instance d'article
                with transaction.atomic():
                    article_instance = article(**article_data)
                    article_instance.save()
                    valid_articles.append(article_instance)

            except Exception as e:
                raise Exception(
                    f"Ligne {row_index + 1}: Erreur inattendue lors de l'enregistrement: {str(e)}."
                )

        return valid_articles

    def construct_article_data(self, row, user):
        produit_instance = self.get_foreign_key_instance(
            produit, row.get("famille"), "libelle", 0, "famille", []
        )
        marque_instance = self.get_foreign_key_instance(
            marque, row.get("marque"), "nom", 0, "marque", []
        )
        fournisseur_instance = self.get_foreign_key_instance(
            fournisseur, row.get("fournisseur"), "nom", 0, "fournisseur", []
        )
        nature_instance = self.get_foreign_key_instance(
            nature, row.get("nature"), "libelle", 0, "nature", []
        )

        qte_value = row.get("qte")
        if pd.isna(qte_value):
            qte_value = 1

        return {
            "designation": row.get("designation"),
            "date_achat": row.get("date achat"),
            "numero_comptable": row.get("numero_comptable"),
            "couleur": row.get("couleur"),
            "poids": row.get("poids"),
            "volume": row.get("volume"),
            "langueur": row.get("langueur"),
            "hauteur": row.get("hauteur"),
            "largeur": row.get("largeur"),
            "date_expiration": self.extract_date(row.get("date expiration")),
            "date_peremption": self.extract_date(row.get("date peremption")),
            "prix_achat": row.get("prix achat"),
            "qte": qte_value,
            "qte_recue": row.get("qte_recue"),
            "N_facture": row.get("N facture"),
            "valider": True,
            "via_erp": False,
            "compte": user.compte,
            "produit": produit_instance,
            "marque": marque_instance,
            "fournisseur": fournisseur_instance,
            "nature": nature_instance,
        }

    def extract_date(self, date_value):
        if isinstance(date_value, datetime):
            return date_value.date()
        return date_value

    def collect_serializer_errors(self, serializer, errors, row_index):
        for field, field_errors in serializer.errors.items():
            value = serializer.initial_data.get(field, "Valeur non trouvée")
            error_message = f"Ligne {row_index + 1}: {field}: {'; '.join(field_errors)}; Valeur fournie: {value}"
            errors.append(error_message)


from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated


class InventaireEmplacementCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print(request.data)
        nom = request.data.get("nom")
        emplacement_id = request.data.get("emplacement_id")
        date_creation = request.data.get("date_creation")
        if not (nom and emplacement_id):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            emplacement_instance = emplacement.objects.get(pk=emplacement_id)
        except emplacement.DoesNotExist:
            return Response(
                {"message": "L'emplacement spécifié n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_instance = request.user  # Récupérer l'utilisateur à partir du jeton JWT

        inventaire_instance = inventaire.objects.create(
            nom=nom,
            user=user_instance,
            date_creation=date_creation,
            categorie="Emplacement",
        )
        inventaire_emplacement.objects.create(
            inventaire=inventaire_instance, emplacement=emplacement_instance
        )

        return Response(
            {"message": "Inventaire créé avec succès"}, status=status.HTTP_201_CREATED
        )


class InventaireEmplacementDetailAPIView(ServerSideDataTableView):
    """
    Vue pour lister les emplacements d'un inventaire avec support DataTable
    Retourne les détails de l'inventaire et la liste des emplacements associés
    """
    model = inventaire_emplacement
    serializer_class = InventaireEmplacementSimpleSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'inventaire_emplacements_detail'
    
    
    # Configuration DataTable
    search_fields = [
        'emplacement__nom',
        'emplacement__id',
        'statut'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'emplacement__nom',
        'statut',
        'created_at'
    ]
    
    # Configuration de pagination
    default_order = 'id'
    page_size = 100
    min_page_size = 1
    max_page_size = 1000
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'emplacement': 'emplacement__nom',
        'emplacement_id': 'emplacement__id',
        'statut': 'statut',
        'created_at': 'created_at'
    }

    def get_datatable_queryset(self):
        """
        Queryset de base filtré par inventaire_id.
        """
        inventaire_id = self.kwargs.get('inventaire_id')
        
        if not self.request.user.compte:
            return inventaire_emplacement.objects.none()
        
        # Vérifier que l'inventaire appartient au compte de l'utilisateur
        try:
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, 
                user__compte=self.request.user.compte
            )
        except inventaire.DoesNotExist:
            return inventaire_emplacement.objects.none()
            
        return inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance
        ).select_related(
            'emplacement',
            'inventaire'
        ).order_by("id")
    
    def get(self, request, inventaire_id, *args, **kwargs):
        """Override pour ajouter les infos de l'inventaire dans la réponse"""
        self.kwargs['inventaire_id'] = inventaire_id
        
        # Récupérer les infos de l'inventaire
        try:
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, 
                user__compte=request.user.compte
            )
            inventaire_data = {
                "id": inventaire_instance.id,
                "nom": inventaire_instance.nom,
                "reference": inventaire_instance.reference,
                "date_creation": inventaire_instance.date_creation,
            }
            
            # Récupérer les IDs des emplacements
            emplacements = inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            )
            emplacement_ids = [emp.emplacement.id for emp in emplacements]
            
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Traitement DataTable standard
        response = super().get(request, *args, **kwargs)
        
        # Ajouter les infos de l'inventaire à la réponse
        if isinstance(response, Response):
            response.data['inventaire'] = inventaire_data
            response.data['emplacements'] = emplacement_ids
        
        return response


class InventaireEmplacementUpdateAPIView(APIView):
    def put(self, request, inventaire_id):
        print(request.data)
        try:
            inventaire_instance = inventaire.objects.get(id=inventaire_id)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = InventaireSerializer(
            inventaire_instance, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()

            # Update entries in the pivot table
            emplacements_data = request.data.get(
                "emplacement_id"
            )  # Assuming emplacements are sent in the appropriate format
            inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            ).delete()

            try:
                emplacement_instance = emplacement.objects.get(id=emplacements_data)
                inventaire_emplacement.objects.create(
                    inventaire=inventaire_instance, emplacement=emplacement_instance
                )
            except emplacement.DoesNotExist:
                return Response(
                    {
                        "message": f"Emplacement avec l'ID {emplacements_data} non trouvé"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InventaireEmplacementsDetailAPIView(ServerSideDataTableView):
    """
    Vue pour lister les détails des emplacements d'un inventaire avec support DataTable
    """
    model = inventaire_emplacement
    serializer_class = InventaireEmplacementDetailSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'inventaire_details_operateurs'
    
    
    # Configuration DataTable
    search_fields = [
        'emplacement__nom',
        'emplacement__id',
        'affceted_at__nom',
        'affceted_at__prenom',
        'statut'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'emplacement__nom',
        'statut',
        'start_at',
        'created_at'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'emplacement': 'emplacement__nom',
        'emplacement_nom': 'emplacement__nom',
        'operateur': 'affceted_at__nom',
        'operateur_nom': 'affceted_at__nom',
        'operateur_prenom': 'affceted_at__prenom',
        'statut': 'statut',
        'etat': 'start_at',
        'created_at': 'created_at'
    }
    
    # Colonnes composées
    composite_columns = {
        'operateur_full_name': {
            'type': 'concat',
            'fields': ['affceted_at__nom', 'affceted_at__prenom'],
            'separator': ' '
        }
    }

    def get_datatable_queryset(self):
        """
        Queryset de base filtré par inventaire_id.
        """
        inventaire_id = self.kwargs.get('inventaire_id')
        
        if not self.request.user.compte:
            return inventaire_emplacement.objects.none()
        
        # Vérifier que l'inventaire appartient au compte de l'utilisateur
        try:
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, 
                user__compte=self.request.user.compte
            )
        except inventaire.DoesNotExist:
            return inventaire_emplacement.objects.none()
            
        return inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance
        ).select_related(
            'emplacement',
            'affceted_at',
            'inventaire'
        ).order_by("-id")
    
    def get(self, request, inventaire_id, *args, **kwargs):
        """Override pour ajouter les infos de l'inventaire dans la réponse"""
        self.kwargs['inventaire_id'] = inventaire_id
        
        # Récupérer les infos de l'inventaire
        try:
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, 
                user__compte=request.user.compte
            )
            inventaire_data = {
                "id": inventaire_instance.id,
                "nom": inventaire_instance.nom,
                "reference": inventaire_instance.reference,
                "date_creation": inventaire_instance.date_creation,
                "statut": inventaire_instance.statut,
            }
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Traitement DataTable standard
        response = super().get(request, *args, **kwargs)
        
        # Ajouter les infos de l'inventaire à la réponse
        if isinstance(response, Response):
            response.data['result'] = inventaire_data
        
        return response


from rest_framework.exceptions import NotFound


class InfoInventaire(generics.ListAPIView):
    def get(self, request, inventaire_id):
        try:
            # Assurez-vous que l'objet 'inventaire' existe pour l'utilisateur
            inventaire_instance = inventaire.objects.get(
                id=inventaire_id, user__compte=request.user.compte
            )

            # Structure des données à renvoyer
            inventaire_data = {
                "id": inventaire_instance.id,
                "nom": inventaire_instance.nom,
                "reference": inventaire_instance.reference,
                "date_creation": inventaire_instance.date_creation,
                "statut": inventaire_instance.statut,
            }

            # Retourner la réponse sous forme de JSON
            return Response(inventaire_data)

        except inventaire.DoesNotExist:
            # Si l'objet 'Inventaire' n'existe pas pour cet utilisateur
            raise NotFound(
                detail="Inventaire non trouvé ou vous n'avez pas accès à cet inventaire."
            )

        except Exception as e:
            # Pour toute autre erreur générale (ex: erreur de connexion DB)
            return Response(
                {"error": str(e)},
                status=500,  # Code de statut 500 pour une erreur serveur
            )


# inventaire par zone
class InventaireZoneListsAPIView(ServerSideDataTableView):
    """
    Vue pour lister les inventaires de zone avec support DataTable
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    """
    model = inventaire
    serializer_class = InventaireZoneSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'inventaires_zone'
    
    
    # Configuration DataTable
    search_fields = [
        'nom',
        'reference',
        'inventaire_emplacement_set__emplacement__zone__nom',
        'user__username',
        'created_at',
        'departement__nom'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'nom',
        'reference',
        'created_at',
        'inventaire_emplacement_set__emplacement__zone__nom',
        'departement__nom'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'nom': 'nom',
        'reference': 'reference',
        'zone': 'inventaire_emplacement_set__emplacement__zone__nom',
        'zone_nom': 'inventaire_emplacement_set__emplacement__zone__nom',
        'user': 'user__username',
        'user_nom': 'user__first_name',
        'user_prenom': 'user__last_name',
        'created_at': 'created_at',
        'updated_at': 'updated_at',
        'statut': 'statut',
        'categorie': 'categorie',
        'departement': 'departement__nom'
    }
    
    # Configuration des colonnes composées
    composite_columns = {
        'user': {
            'type': 'concat',
            'fields': ['user__first_name', 'user__last_name'],
            'separator': ' '
        },
        'inventaire_full_info': {
            'type': 'concat',
            'fields': ['nom', 'reference'],
            'separator': ' - '
        }
    }

    def get_datatable_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les inventaires de zone valides sont retournés.
        """
        if not self.request.user.compte:
            return inventaire.objects.none()
            
        return inventaire.objects.filter(
            user__compte=self.request.user.compte, 
            categorie="Zone"
        ).select_related(
            'user',
            'departement'
        ).prefetch_related(
            'inventaire_emplacement_set',
            'inventaire_emplacement_set__emplacement',
            'inventaire_emplacement_set__emplacement__zone'
        ).order_by("-id")


class zonesListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.compte:
            zones = zone.objects.filter(location__compte=user.compte)
            serializer = ZoneSerializer(zones, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class zonesListFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, zode_id):
        user = request.user
        if user.compte:
            zones = zone.objects.filter(location__compte=user.compte, id=zode_id)
            serializer = ZoneSerializer(zones, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class InventaireZoneCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nom = request.data.get("nom")
        zone_id = request.data.get("zone_id")
        date_creation = request.data.get("date_creation")

        if not (nom and zone_id and date_creation):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            zone_instance = zone.objects.get(pk=zone_id)
        except zone.DoesNotExist:
            return Response(
                {"message": "La zone spécifiée n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_instance = request.user

        # Créer l'inventaire
        inventaire_instance = inventaire.objects.create(
            nom=nom,
            user=user_instance,
            date_creation=date_creation,
            categorie="Zone",
        )

        # Récupérer les emplacements associés à la zone et créer les entrées d'inventaire_emplacement
        emplacements = emplacement.objects.filter(zone=zone_instance)
        for emplacement_instance in emplacements:
            inventaire_emplacement.objects.create(
                inventaire=inventaire_instance, emplacement=emplacement_instance
            )

        return Response(
            {"message": "Inventaire créé avec succès"}, status=status.HTTP_201_CREATED
        )


class InventaireZoneDetailsAPIView(APIView):
    def get(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_instance = inventaire.objects.get(id=inventaire_id)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "L'inventaire spécifié n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Récupérer les emplacements associés à l'inventaire à partir de la table pivot
        emplacements = inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance
        ).select_related("emplacement")

        # Extraire la zone de chaque emplacement
        zones = set(emplacements.values_list("emplacement__zone__id", flat=True))

        # Sérialiser les données
        data = {
            "inventaire": {
                "id": inventaire_instance.id,
                "nom": inventaire_instance.nom,
                "reference": inventaire_instance.reference,
                "date_creation": inventaire_instance.date_creation,
                # Ajoutez d'autres champs de l'inventaire si nécessaire
            },
            "zone": list(
                zones
            ),  # Convertir l'ensemble de zones en liste pour la réponse JSON
        }

        return Response(data)


class InventaireZoneUpdatesAPIView(APIView):
    def put(self, request, inventaire_id):
        try:
            print(request.data)
            # Récupérer l'inventaire
            inventaire_instance = inventaire.objects.get(id=inventaire_id)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "L'inventaire spécifié n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Récupérer les données de la requête
        nom = request.data.get("nom")
        zone_id = request.data.get("zone_id")

        # Vérifier si toutes les données requises sont présentes
        if not (nom and zone_id):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Récupérer la zone spécifiée
            zone_instance = zone.objects.get(pk=zone_id)
        except zone.DoesNotExist:
            return Response(
                {"message": "La zone spécifiée n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Modifier les champs de l'inventaire
        inventaire_instance.nom = nom
        # Modifier d'autres champs de l'inventaire si nécessaire
        inventaire_instance.save()

        # Modifier les emplacements associés à l'inventaire en fonction de la nouvelle zone
        emplacements = emplacement.objects.filter(zone=zone_instance)

        # Effacer les anciens emplacements associés à l'inventaire
        inventaire_emplacement.objects.filter(inventaire=inventaire_instance).delete()

        # Ajouter les nouveaux emplacements associés à la nouvelle zone
        for emplacement_instance in emplacements:
            inventaire_emplacement.objects.create(
                inventaire=inventaire_instance, emplacement=emplacement_instance
            )

        return Response(
            {"message": "Inventaire modifié avec succès"}, status=status.HTTP_200_OK
        )


# inventaire par location


class InventaireLocationListsAPIView(ServerSideDataTableView):
    """
    Vue pour lister les inventaires de location avec support DataTable
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API
    """
    model = inventaire
    serializer_class = InventaireLocationSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'inventaires_location'
    
    filterset_class = InventaireFilter
    
    # Configuration DataTable
    search_fields = [
        'nom',
        'reference',
        'inventaire_emplacement_set__emplacement__zone__location__nom',
        'user__username',
        'created_at',
        'departement__nom'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'nom',
        'reference',
        'created_at',
        'inventaire_emplacement_set__emplacement__zone__location__nom',
        'departement__nom'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'nom': 'nom',
        'reference': 'reference',
        'location': 'inventaire_emplacement_set__emplacement__zone__location__nom',
        'location_nom': 'inventaire_emplacement_set__emplacement__zone__location__nom',
        'user': 'user__username',
        'user_nom': 'user__first_name',
        'user_prenom': 'user__last_name',
        'created_at': 'created_at',
        'updated_at': 'updated_at',
        'statut': 'statut',
    
    }
    
    # Configuration des colonnes composées
    composite_columns = {
        'user_full_name': {
            'type': 'concat',
            'fields': ['user__first_name', 'user__last_name'],
            'separator': ' '
        },
        'inventaire_full_info': {
            'type': 'concat',
            'fields': ['nom', 'reference'],
            'separator': ' - '
        }
    }

    def get_datatable_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les inventaires de location valides sont retournés.
        """
        if not self.request.user.compte:
            return inventaire.objects.none()
            
        return inventaire.objects.filter(
            user__compte=self.request.user.compte, 
            categorie="Location"
        ).select_related(
            'user',
            'departement'
        ).prefetch_related(
            'inventaire_emplacement_set',
            'inventaire_emplacement_set__emplacement',
            'inventaire_emplacement_set__emplacement__zone',
            'inventaire_emplacement_set__emplacement__zone__location'
        ).order_by("-id")


class locationsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.compte:
            locations = location.objects.filter(compte=user.compte)
            serializer = LocationSerializer(locations, many=True)
            return Response(serializer.data)
        else:
            return Response(
                {"error": "No associated account found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PersonnesListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        compte = request.user.compte
        locations = Personne.objects.filter(compte=compte)
        serializer = PersonneSerializer(locations, many=True)
        return Response(serializer.data)


class InventaireLocationCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nom = request.data.get("nom")
        location_id = request.data.get("location_id")  # Retirer la virgule ici
        date_creation = request.data.get("date_creation")

        if not (nom and location_id):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            location_instance = location.objects.get(pk=location_id)
        except location.DoesNotExist:
            return Response(
                {"message": "La location spécifiée n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_instance = request.user

        # Récupérer tous les emplacements associés à la location spécifiée
        emplacements = emplacement.objects.filter(zone__location=location_instance)

        inventaire_instance = inventaire.objects.create(
            nom=nom,
            user=user_instance,
            date_creation=date_creation,
            categorie="Location",
        )

        for emplacement_instance in emplacements:
            inventaire_emplacement.objects.create(
                inventaire=inventaire_instance, emplacement=emplacement_instance
            )

        return Response(
            {"message": "Inventaire créé avec succès"}, status=status.HTTP_201_CREATED
        )


class InventaireLocationDetailAPIView(APIView):
    def get(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_obj = inventaire.objects.get(pk=inventaire_id)

            # Obtenir tous les emplacements associés à cet inventaire
            emplacements = inventaire_emplacement.objects.filter(
                inventaire=inventaire_obj
            )

            # Récupérer les zones uniques des emplacements
            zones = emplacements.values_list("emplacement__zone", flat=True).distinct()

            # Récupérer les locations correspondant à ces zones
            locations = location.objects.filter(zone__in=zones)

            # Sélectionner une seule location si disponible
            location_ids = []
            if locations.exists():
                location_ids.append(locations.first().id)

            # Sérialiser les données de l'inventaire
            inventaire_serializer = InventaireSerializer(inventaire_obj)

            # Construire la réponse avec l'inventaire et les identifiants de location
            response_data = {
                "inventaire": inventaire_serializer.data,
                "location": location_ids,
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )


class InventaireLocationUpdateAPIView(APIView):
    def put(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_instance = inventaire.objects.get(id=inventaire_id)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )

        # Mettre à jour les champs de l'inventaire avec les données fournies
        nom = request.data.get("nom", inventaire_instance.nom)
        statut = request.data.get("statut", inventaire_instance.statut)

        # Appliquer les modifications
        inventaire_instance.nom = nom
        inventaire_instance.statut = statut

        # Récupérer l'ID de la nouvelle location sélectionnée, si fourni
        new_location_id = request.data.get("location_id")
        if new_location_id:
            # Vérifier si la nouvelle location est valide
            try:
                new_location = location.objects.get(id=new_location_id)
                # Récupérer tous les emplacements associés à la nouvelle location
                new_location_emplacements = emplacement.objects.filter(
                    zone__location=new_location
                )

                # Supprimer tous les emplacements existants associés à l'inventaire
                inventaire_emplacement.objects.filter(
                    inventaire=inventaire_instance
                ).delete()

                # Associer les nouveaux emplacements à l'inventaire
                for emplacement_instance in new_location_emplacements:
                    inventaire_emplacement.objects.create(
                        inventaire=inventaire_instance, emplacement=emplacement_instance
                    )
            except location.DoesNotExist:
                return Response(
                    {"message": "La nouvelle location spécifiée est invalide"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Enregistrer les modifications de l'inventaire
        inventaire_instance.save()

        return Response(
            {"message": "Inventaire et emplacements modifiés avec succès"},
            status=status.HTTP_200_OK,
        )


# inventaire par departement


class InventaireDepartementListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les inventaires de département avec support DataTable
    """
    model = inventaire
    serializer_class = InventaireDepartementSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'inventaires_departement'
    
    filterset_class = InventaireFilter
    
    # Configuration DataTable
    search_fields = [
        'nom',
        'reference',
        'user__username',
        'created_at',
        'departement__nom'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'nom',
        'reference',
        'created_at',
        'departement__nom'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'nom': 'nom',
        'reference': 'reference',
        'user': 'user__username',
        'created_at': 'created_at',
        'statut': 'statut',
        'categorie': 'categorie',
        'departement': 'departement__nom'
    }

    def get_datatable_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les inventaires de département valides sont retournés.
        """
        if not self.request.user.compte:
            return inventaire.objects.none()
            
        return inventaire.objects.filter(
            user__compte=self.request.user.compte, 
            categorie="Departement"
        ).select_related(
            'user',
            'departement'
        ).prefetch_related(
            'inventaire_emplacement_set',
            'inventaire_emplacement_set__emplacement'
        ).order_by("-id")


class InventaireCreateByDepartementAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nom = request.data.get("nom")
        date_creation = request.data.get("date_creation")
        departement_id = request.data.get("departement_id")  # Un seul ID

        if not (nom and departement_id):
            return Response(
                {"message": "Tous les champs sont requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Récupérer l'utilisateur (dans cet exemple, l'utilisateur est statiquement choisi)
            user_instance = request.user
            departement_instance = departement.objects.filter(id=departement_id).first()

            # Créer l'inventaire
            inventaire_instance = inventaire.objects.create(
                nom=nom,
                user=user_instance,
                date_creation=date_creation,
                statut="En attente",
                categorie="Departement",
                departement=departement_instance,
            )

            # Trouver les articles associés au département spécifié
            items_associes = item.objects.filter(departement_id=departement_id)

            # Grouper les articles par emplacement
            emplacements_vus = set()  # Pour éviter les duplications
            for art in items_associes:
                emplacement_instance = art.emplacement
                if emplacement_instance not in emplacements_vus:
                    # Créer un inventaire_emplacement uniquement pour les emplacements uniques
                    inventaire_emplacement.objects.create(
                        emplacement=emplacement_instance,
                        inventaire=inventaire_instance,
                        statut="en attente",
                    )
                    emplacements_vus.add(emplacement_instance)

            # Utiliser le sérialiseur pour obtenir les données de l'inventaire
            serializer = InventaireSerializer(inventaire_instance)

            response_data = {
                "inventaire": serializer.data,
                "departements": [
                    departement_id
                ],  # Retourner comme une liste avec un seul élément
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except item.DoesNotExist:
            return Response(
                {"message": "Le département spécifié n'existe pas"},
                status=status.HTTP_404_NOT_FOUND,
            )


class InventaireDepartementDetailAPIView(APIView):
    def get(self, request, inventaire_id):
        try:
            # Récupérer l'inventaire
            inventaire_instance = inventaire.objects.get(id=inventaire_id)

            # Sérialiser l'inventaire
            serializer = InventaireSerializer(inventaire_instance)

            # Récupérer le premier département associé à cet inventaire
            inventaire_emplacements = inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            )
            department_id = None
            for ie in inventaire_emplacements:
                items = item.objects.filter(emplacement=ie.emplacement)
                for art in items:
                    department_id = art.departement.id
                    break
                if department_id is not None:
                    break

            # Ajouter le département à la réponse
            response_data = {
                "inventaire": serializer.data,
                "departements": [department_id] if department_id is not None else [],
            }

            return Response(response_data)
        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )


class InventaireDepartementUpdateAPIView(APIView):
    def put(self, request, inventaire_id):
        try:
            print(request.data)
            # Récupérer l'inventaire à modifier
            inventaire_instance = inventaire.objects.get(id=inventaire_id)

            # Vos modifications à l'inventaire
            inventaire_instance.nom = request.data.get("nom", inventaire_instance.nom)
            # inventaire_instance.reference = request.data.get(
            #     "reference", inventaire_instance.reference
            # )

            # Sauvegarder les modifications de l'inventaire
            inventaire_instance.save()

            # Récupérer l'ID du département à associer (s'il est fourni dans la requête)
            departement_id = request.data.get("departement_id")

            # Vérifier si un département a été sélectionné
            try:
                # Récupérer le département sélectionné
                departement_instance = departement.objects.get(id=departement_id)

                # Effacer les anciens emplacements associés à cet inventaire
                inventaire_emplacement.objects.filter(
                    inventaire=inventaire_instance
                ).delete()

                # Récupérer les emplacements associés au département sélectionné
                items = item.objects.filter(departement=departement_instance)
                for art in items:
                    # Créer de nouveaux emplacements pour cet inventaire
                    inventaire_emplacement.objects.create(
                        inventaire=inventaire_instance, emplacement=art.emplacement
                    )

                # Mettre à jour l'inventaire avec le nouveau département
                inventaire_instance.save()

                return Response(
                    {"message": "Inventaire et emplacements modifiés avec succès"},
                    status=status.HTTP_200_OK,
                )
            except departement.DoesNotExist:
                return Response(
                    {"message": "Le département spécifié n'existe pas"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except inventaire.DoesNotExist:
            return Response(
                {"message": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )


# Affectation
from django.shortcuts import get_object_or_404

from django.db.models import F
from django.http import JsonResponse


from .models import emplacement

from django.core.exceptions import ObjectDoesNotExist

from django.db import transaction  # Importez la transaction

from rest_framework import status


class UpdateArticleEmplacement(APIView):
    def put(self, request):
        try:

            user = request.user
            tag_references = request.data.get("tag_reference", [])
            emplacement_id = request.data.get("emplacement_id", None)
            departement_id = request.data.get("departement_id", None)
            personne_id = request.data.get("personne_id", None)
            if not isinstance(tag_references, list):
                return Response(
                    "Les références de tag doivent être fournies sous forme de liste.",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Rechercher les tags en fonction des références
            tags_objs = tag.objects.filter(
                reference__in=tag_references, compte=user.compte
            )

            if not tags_objs:
                return Response(
                    "Aucun tag correspondant aux références spécifiées n'a été trouvé.",
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Mettre à jour l'emplacement de tous les articles associés aux tags trouvés
            for tag_obj in tags_objs:
                items_objs = item.objects.filter(tag=tag_obj)
                for item_obj in items_objs:
                    old_emplacement = item_obj.emplacement
                    old_departement = item_obj.departement
                    old_personne = item_obj.affectation_personne

                    # Variables pour le nouvel état après mise à jour
                    new_emplacement = old_emplacement
                    new_departement = old_departement
                    new_personne = old_personne

                    if emplacement_id is not None and emplacement_id > 0:
                        emplacement_instance = emplacement.objects.get(
                            pk=emplacement_id
                        )
                        item_obj.emplacement = emplacement_instance
                        new_emplacement = emplacement_instance

                    if departement_id is not None and departement_id > 0:
                        departement_instance = departement.objects.get(
                            pk=departement_id
                        )
                        item_obj.departement = departement_instance
                        new_departement = departement_instance

                    if personne_id is not None and personne_id > 0:
                        personne_instance = Personne.objects.get(pk=personne_id)
                        item_obj.affectation_personne = personne_instance
                        new_personne = personne_instance

                    item_obj.save()

                    # Créer un enregistrement historique même si old et new sont identiques
                    TransferHistorique.objects.create(
                        item_transfer=item_obj,
                        new_emplacement=(
                            new_emplacement
                            if new_emplacement != old_emplacement
                            else None
                        ),
                        old_emplacement=(
                            old_emplacement
                            if new_emplacement != old_emplacement
                            else None
                        ),
                        new_departement=(
                            new_departement
                            if new_departement != old_departement
                            else None
                        ),
                        old_departement=(
                            old_departement
                            if new_departement != old_departement
                            else None
                        ),
                        new_personne=(
                            new_personne if new_personne != old_personne else None
                        ),
                        old_personne=(
                            old_personne if new_personne != old_personne else None
                        ),
                    )

            return Response(
                "L'emplacement des articles a été mis à jour avec succès.",
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Une erreur s'est produite : {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TagCreateView(APIView):
    def post(self, request):
        user = request.user

        # S'assurer que l'utilisateur est authentifié
        if not user.is_authenticated:
            return Response(
                {"error": "Utilisateur non authentifié."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        references = request.data.get(
            "reference", []
        )  # Obtenir la liste des références depuis les données de la requête
        type_tag = request.data.get("type_tag", None)

        if type_tag is None:
            return Response(
                {"error": "Merci de sélectionner un type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier si 'references' est bien une liste
        if not isinstance(references, list):
            return Response(
                {"error": "'reference' doit être une liste."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupérer toutes les références existantes pour l'utilisateur
        existing_tags = tag.objects.filter(compte=user.compte.id, type=type_tag)
        existing_references = existing_tags.values_list("reference", flat=True)

        # Vérifier si des références fournies existent déjà
        duplicates = [ref for ref in references if ref in existing_references]
        if duplicates:
            return Response(
                {
                    "error": f"Les tags avec les références suivantes existent déjà : {', '.join(duplicates)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_tags = []

        try:
            with transaction.atomic():  # Utiliser une transaction pour garantir l'intégrité des données
                for reference in references:
                    # Créer un serializer pour chaque référence
                    serializer = TagSerializer(
                        data={
                            "reference": reference,
                            "compte": user.compte.id,
                            "type": type_tag,
                        }
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save()  # Enregistrer l'objet tag
                    created_tags.append(serializer.data)

            return Response(
                {"message": "Tags créés avec succès.", "tags": created_tags},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


from django.db.models import ObjectDoesNotExist
from django.core.exceptions import ObjectDoesNotExist
from .models import tag, item, emplacement, inventaire
from rest_framework.response import Response
from rest_framework import status


def verifier_tags(liste_references_tags, user):
    tags_connus = []
    tags_inconnus = []
    for reference_tag in liste_references_tags:
        try:
            tag_instance = tag.objects.filter(
                reference=reference_tag, compte=user.compte
            ).first()
            if tag_instance:
                tags_connus.append(tag_instance)
            else:
                tags_inconnus.append(reference_tag)
        except Exception as e:
            print(f"Unexpected error: {e}")
            tags_inconnus.append(reference_tag)
    return tags_connus, tags_inconnus


def verifier_tags_affecter(liste_references_tags, user):
    # Si la liste contient des chaînes, convertir en objets `tag`
    if all(isinstance(tag_obj, str) for tag_obj in liste_references_tags):
        tags = tag.objects.filter(
            reference__in=liste_references_tags, compte=user.compte
        )
    elif all(isinstance(tag_obj, tag) for tag_obj in liste_references_tags):
        tags = liste_references_tags
    else:
        raise ValueError(
            "La liste doit contenir uniquement des chaînes de caractères ou des objets tag."
        )

    tags_affectes = []
    tags_non_affectes = []

    # Parcourir les tags et les classer en affectés ou non-affectés
    for tag_obj in tags:
        if tag_obj.affecter:
            tags_affectes.append(tag_obj)
        else:
            tags_non_affectes.append(tag_obj)

    return tags_affectes, tags_non_affectes


def verifier_emplacement_tags(tags_references, emplacement_id, user):
    bons_emplacements = []
    mauvais_emplacements = []

    tags_affectes, _ = verifier_tags_affecter(tags_references, user)
    for tag_obj in tags_affectes:
        item_obj = item.objects.filter(
            tag=tag_obj, article__compte=user.compte, archive=False
        ).first()
        if item_obj:
            if item_obj.emplacement_id == emplacement_id:
                bons_emplacements.append(tag_obj)
            else:
                mauvais_emplacements.append(tag_obj)
        else:
            mauvais_emplacements.append(tag_obj)

    return bons_emplacements, mauvais_emplacements


def verifier_tags_manquants(references_tags, id_emplacement):
    items = item.objects.filter(emplacement_id=id_emplacement, archive=False)

    tags_trouvables = []
    tags_manquants = []

    for item_obj in items:
        if item_obj.tag:
            if item_obj.tag.reference in references_tags:
                tags_trouvables.append(item_obj.tag.reference)
            else:
                tags_manquants.append(item_obj.tag.reference)
        else:
            tags_manquants.append(
                "Aucun tag associé à l'article {}".format(item_obj.numero_serie)
            )

    return tags_trouvables, tags_manquants


def verifier_items_archives(tags_references, emplacement_id, user):
    items_archives = []

    tags_affectes, _ = verifier_tags_affecter(tags_references, user)

    for tag_obj in tags_affectes:
        item_obj = item.objects.filter(
            tag=tag_obj, article__compte=user.compte, archive=True
        ).first()

        if item_obj and item_obj.emplacement_id == emplacement_id:
            items_archives.append(item_obj.tag.reference)

    return items_archives


def filter_tags_by_emplacement_and_departement(
    tags_references, emplacement_id, departement_id
):
    try:
        items_in_emplacement = item.objects.filter(
            tag__reference__in=tags_references,
            emplacement_id=emplacement_id,
            archive=False,
        )
        items_in_department = items_in_emplacement.filter(departement_id=departement_id)

        filtered_tags = items_in_department.values_list("tag__reference", flat=True)
        print(filtered_tags)
        return list(filtered_tags)

    except Exception as e:
        return {"error": f"Une erreur est survenue : {str(e)}"}


class VerifyTagsLocationAPI(APIView):
    def post(self, request):
        data = request.data
        user = request.user
        tags_references = data.get("tags", [])
        emplacement_id = data.get("emplacement_id")
        inventaire_id = data.get("inventaire_id")

        if not tags_references or not emplacement_id or not inventaire_id:
            return Response(
                {"error": "Tous les champs requis ne sont pas fournis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        emplacement_instance = emplacement.objects.filter(id=emplacement_id).first()
        if not emplacement_instance:
            return Response(
                {"error": "Emplacement introuvable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inventaire_instance = inventaire.objects.filter(pk=inventaire_id).first()
        if not inventaire_instance:
            return Response(
                {"error": "Inventaire introuvable."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer tous les tags du compte utilisateur
        tags_queryset = tag.objects.filter(
            reference__in=tags_references, compte=user.compte
        )
        
        # Filtrer par département si nécessaire
        tags_references_filtered = tags_references
        if inventaire_instance.departement is not None:
            filtered_result = filter_tags_by_emplacement_and_departement(
                tags_references,
                emplacement_instance.id,
                inventaire_instance.departement.id,
            )
            # Vérifier si le résultat est une liste ou un dictionnaire d'erreur
            if isinstance(filtered_result, list):
                tags_references_filtered = filtered_result
            else:
                # En cas d'erreur, utiliser toutes les références
                tags_references_filtered = tags_references

        # Identifier les tags inconnus (qui n'existent pas dans la base)
        tags_inconnus = [
            ref
            for ref in tags_references
            if ref not in tags_queryset.values_list("reference", flat=True)
        ]

        # Utiliser les références filtrées pour les vérifications
        tags_references_to_check = tags_references_filtered
        
        # Vérifier les tags affectés/non affectés
        tags_affectes, tags_non_affectes = verifier_tags_affecter(
            tags_references_to_check, user
        )
        
        # Vérifier les emplacements
        bons_emplacements, mauvais_emplacements = verifier_emplacement_tags(
            tags_references_to_check, emplacement_instance.id, user
        )
        
        # Vérifier les items archivés
        item_archive = verifier_items_archives(
            tags_references_to_check, emplacement_instance.id, user
        )
        
        # Vérifier les tags manquants (items dans l'emplacement non scannés)
        tags_trouvables, tags_manquants = verifier_tags_manquants(
            tags_references_to_check, emplacement_instance.id
        )

        response_data = []
        counts = {
            "correcte": 0,
            "inconnu": 0,
            "manquant": 0,
            "non_affecter": 0,
            "intru": 0,
        }

        # Traiter les tags avec bon emplacement (correcte)
        for tag_obj in bons_emplacements:
            if isinstance(tag_obj, tag):
                item_obj_correct = item.objects.filter(
                    tag=tag_obj, archive=False
                ).first()
                if item_obj_correct:
                    response_data.append(
                        self.format_response(
                            item_obj_correct, tag_obj.reference, "correcte"
                        )
                    )
                    counts["correcte"] += 1

        # Traiter les tags avec mauvais emplacement (intru)
        for tag_obj in mauvais_emplacements:
            if isinstance(tag_obj, tag):
                item_obj_intru = item.objects.filter(tag=tag_obj, archive=False).first()
                if item_obj_intru:
                    response_data.append(
                        self.format_response(item_obj_intru, tag_obj.reference, "intru")
                    )
                    counts["intru"] += 1

        # Traiter les tags inconnus
        for tag_reference in tags_inconnus:
            response_data.append({"tag": tag_reference, "statut": "inconnu"})
            counts["inconnu"] += 1

        # Traiter les tags non affectés
        for tag_obj in tags_non_affectes:
            if isinstance(tag_obj, tag):
                response_data.append(
                    {"tag": tag_obj.reference, "statut": "non_affecter"}
                )
                counts["non_affecter"] += 1

        # Traiter les items archivés
        for tag_reference in item_archive:
            response_data.append({"tag": tag_reference, "statut": "non_affecter"})
            counts["non_affecter"] += 1

        # Traiter les tags manquants (items dans l'emplacement non scannés)
        for tag_reference in tags_manquants:
            # Vérifier si c'est un message d'erreur (item sans tag)
            if isinstance(tag_reference, str) and tag_reference.startswith("Aucun tag"):
                # Item sans tag associé
                response_data.append({"tag": tag_reference, "statut": "manquant"})
                counts["manquant"] += 1
            else:
                # Récupérer l'item associé pour avoir plus d'informations
                tage = tag.objects.filter(
                    reference=tag_reference, compte=user.compte
                ).first()
                if tage:
                    item_obj_manquant = item.objects.filter(
                        tag=tage, emplacement_id=emplacement_instance.id, archive=False
                    ).first()
                    if item_obj_manquant:
                        response_data.append(
                            self.format_response(
                                item_obj_manquant, tag_reference, "manquant"
                            )
                        )
                    else:
                        response_data.append(
                            {"tag": tag_reference, "statut": "manquant"}
                        )
                else:
                    response_data.append({"tag": tag_reference, "statut": "manquant"})
                counts["manquant"] += 1

        return Response(
            {"data": response_data, "counts": counts}, status=status.HTTP_200_OK
        )

    @staticmethod
    def format_response(item_obj, tag_reference, status):
        return {
            "item_id": getattr(item_obj, "id", None),
            "item_designation": getattr(
                getattr(item_obj, "article", None), "designation", None
            ),
            "tag": tag_reference,
            "statut": status,
        }


class VerifyTagsNonPlanifierAPI(APIView):
    def post(self, request):
        data = request.data
        user = request.user

        # Assurez-vous que les données requises sont présentes dans la demande
        if "tags" not in data or "emplacement_id" not in data:
            return Response(
                {"error": "Les tags et l'ID de l'emplacement sont requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tags = data["tags"]
        emplacement_id = data["emplacement_id"]

        # Appelez les fonctions pour vérifier les tags
        tags_inconnus = verifier_tags(tags, user)[1]
        tags_affectes, tags_non_affectes = verifier_tags_affecter(tags, user)
        tags_trouvables, tags_manquants = verifier_tags_manquants(tags, emplacement_id)
        bons_emplacements, mauvais_emplacements = verifier_emplacement_tags(
            tags, emplacement_id, user
        )
        # Initialize counters
        counts = {
            "correcte": 0,
            "inconnu": 0,
            "manquant": 0,
            "non_affecter": 0,
            "intru": 0,
            "archive": 0,
        }

        # Prepare the response data
        response_data = []

        for tag_reference in bons_emplacements:
            tage = tag.objects.get(reference=tag_reference, compte=user.compte)
            item_obj = item.objects.get(tag=tage)
            try:
                if item_obj.article and item_obj.archive == False:
                    response_data.append(
                        {
                            "item_id": item_obj.id,
                            "item_designation": item_obj.article.designation,
                            "tag": item_obj.tag.reference,
                            "statut": "correcte",
                        }
                    )
                    counts["correcte"] += 1
                elif item_obj.archive == True and item_obj.article:
                    response_data.append(
                        {
                            "item_id": item_obj.id,
                            "item_designation": item_obj.article.designation,
                            "tag": item_obj.tag.reference,
                            "statut": "archive",
                        }
                    )
                    counts["archive"] += 1
                else:
                    response_data.append(
                        {
                            "item_id": item_obj.id,
                            "item_designation": item_obj.article.designation,
                            "tag": item_obj.tag.reference,
                            "statut": "intru",
                        }
                    )
                    counts["intru"] += 1
            except item.DoesNotExist:
                response_data.append(
                    {
                        "item_id": None,
                        "item_designation": None,
                        "tag": tag_reference,
                        "statut": "inconnu",
                    }
                )
                counts["inconnu"] += 1

        for mouvais_tag_reference in mauvais_emplacements:
            mouvais_tage = tag.objects.get(
                reference=mouvais_tag_reference, compte=user.compte
            )
            mouvais_item_obj = item.objects.filter(tag=mouvais_tage).first()
            if mouvais_item_obj:
                response_data.append(
                    {
                        "item_id": mouvais_item_obj.id,
                        "item_designation": (
                            mouvais_item_obj.article.designation
                            if mouvais_item_obj.article
                            else None
                        ),
                        "tag": mouvais_tage.reference,
                        "statut": "intru",
                    }
                )
                counts["intru"] += 1
            else:
                response_data.append(
                    {
                        "item_id": None,
                        "item_designation": None,
                        "tag": mouvais_tage.reference,
                        "statut": "non affecter",
                    }
                )
                counts["non_affecter"] += 1

        for manquants_tag_reference in tags_manquants:
            manquants_tage = tag.objects.get(reference=manquants_tag_reference)
            manquants_item_obj = item.objects.get(tag=manquants_tage)
            response_data.append(
                {
                    "item_id": manquants_item_obj.id,
                    "item_designation": manquants_item_obj.article.designation,
                    "tag": manquants_item_obj.tag.reference,
                    "statut": "manquant",
                }
            )
            counts["manquant"] += 1

        for non_affecter_tag_reference in tags_non_affectes:
            response_data.append(
                {
                    "item_id": None,
                    "item_designation": None,
                    "tag": non_affecter_tag_reference.reference,
                    "statut": "non affecter",
                }
            )
            counts["non_affecter"] += 1

        for inconnus_tag_reference in tags_inconnus:
            response_data.append(
                {
                    "item_id": None,
                    "item_designation": None,
                    "tag": inconnus_tag_reference,
                    "statut": "inconnu",
                }
            )
            counts["inconnu"] += 1

        # Add counts to the response
        return Response(
            {"data": response_data, "counts": counts}, status=status.HTTP_200_OK
        )


class ModifierStatutInventaireEmplacement(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # Récupérer l'utilisateur authentifié
        user = request.user

        # Récupérer l'inventaire_id à partir des données de la requête
        inventaire_id = request.data.get("id")

        # active_inventaire_emplacement = inventaire_emplacement.objects.filter(
        #     affceted_at=user, statut='En cours'
        # ).exists()

        # # Si un inventaire actif existe pour l'utilisateur, retourner une réponse interdite
        # if active_inventaire_emplacement:
        #     return Response({
        #         "message": "Vous n'avez pas l'autorisation de lancer un autre inventaire, car un inventaire est déjà en cours."
        #     }, status=status.HTTP_403_FORBIDDEN)

        try:
            # Tenter de récupérer l'objet inventaire_emplacement par son ID
            inventaire_obj = get_object_or_404(inventaire_emplacement, id=inventaire_id)
        except ValueError:
            # Gérer ValueError si l'ID d'inventaire n'est pas valide
            return Response(
                {"message": "ID d'inventaire invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except inventaire_emplacement.DoesNotExist:
            # Gérer l'exception DoesNotExist si aucun inventaire_emplacement avec l'ID donné n'est trouvé
            return Response(
                {"message": "Inventaire non trouvé."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Gérer d'autres exceptions imprévues
            return Response(
                {"message": f"Erreur: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Attribuer l'utilisateur et définir le statut sur 'En cours'
        inventaire_obj.affceted_at = user
        inventaire_obj.statut = "En cours"
        inventaire_obj.save()

        # Retourner une réponse de succès
        return Response(
            {"message": "Le statut a été modifié avec succès."},
            status=status.HTTP_200_OK,
        )


class UpdateQteRecueView(APIView):
    def put(self, request, id_article):
        try:
            article_instance = article.objects.get(pk=id_article)
        except article.DoesNotExist:
            return Response(
                {"error": "Article not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if article_instance.valider:
            return Response(
                {"error": "Article is already validated and cannot be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qte_recue = request.data.get("qte_recue")
        if qte_recue is not None:
            try:
                qte_recue = int(qte_recue)
                if qte_recue > 0:
                    article_instance.qte_recue = qte_recue
                    article_instance.save()
                    return Response(
                        "la quantite a ete modifie avec succès.",
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "qte_recue must be greater than 0"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except ValueError:
                return Response(
                    {"error": "qte_recue must be an integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"error": "qte_recue is required"}, status=status.HTTP_400_BAD_REQUEST
            )


from django.utils import timezone


class ValidateArticleView(APIView):
    def post(self, request, id_article):
        article_instance = get_object_or_404(article, pk=id_article)

        if article_instance.valider:
            return Response(
                {"error": "Article is already validated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if article_instance.qte_recue is None or article_instance.qte is None:
            return Response(
                {"error": "Both qte and qte_recue must be set."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if article_instance.qte_recue < 0 or article_instance.qte < 0:
            return Response(
                {"error": "qte and qte_recue must be non-negative."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current_date = timezone.now().date()
        if article_instance.qte_recue == article_instance.qte:
            article_instance.valider = True
            article_instance.save()
            return Response(
                {"message": "Article validated successfully."},
                status=status.HTTP_200_OK,
            )
        elif article_instance.qte_recue < article_instance.qte:
            with transaction.atomic():
                remaining_qte = article_instance.qte - article_instance.qte_recue
                # article_instance.qte = article_instance.qte_recue
                article_instance.valider = True
                article_instance.date_reception = current_date
                article_instance.save()

                new_article = article.objects.create(
                    code_article=article_instance.code_article,
                    designation=article_instance.designation,
                    date_achat=article_instance.date_achat,
                    numero_serie=article_instance.numero_serie,
                    numero_comptable=article_instance.numero_comptable,
                    image=article_instance.image,
                    couleur=article_instance.couleur,
                    poids=article_instance.poids,
                    volume=article_instance.volume,
                    langueur=article_instance.langueur,
                    hauteur=article_instance.hauteur,
                    largeur=article_instance.largeur,
                    date_expiration=article_instance.date_expiration,
                    date_peremption=article_instance.date_péremption,
                    date_reception=article_instance.date_reception,
                    prix_achat=article_instance.prix_achat,
                    attachement1=article_instance.attachement1,
                    attachement2=article_instance.attachement2,
                    attachement3=article_instance.attachement3,
                    qte=remaining_qte,
                    qte_recue=remaining_qte,
                    archive=article_instance.archive,
                    valider=False,
                    via_erp=article_instance.via_erp,
                    produit=article_instance.produit,
                    fournisseur=article_instance.fournisseur,
                    nature=article_instance.nature,
                )
                return Response(
                    {
                        "message": "Article validated and new article created with remaining quantity."
                    },
                    status=status.HTTP_200_OK,
                )
        else:
            return Response(
                {"error": "qte_recue cannot be greater than qte."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DuplicationView(APIView):
    def post(self, request):
        try:
            data = request.data
            article_id = data.get("article_id")
            quantity = data.get("quantity")
            emplacement_id = data.get("emplacement_id")
            departement_id = data.get("departement_id")
            numero_serie = data.get("numero_serie", "")
            personne = data.get("personne", "")
            tag_references = data.get("tag_references", [])
            print(departement_id)
            if None in [article_id, quantity, emplacement_id] and 0 in [
                article_id,
                quantity,
                emplacement_id,
            ]:
                return Response(
                    {"error": "Certains champs sont manquants."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if None in [article_id, quantity, emplacement_id, departement_id] or 0 in [
                article_id,
                quantity,
                emplacement_id,
                departement_id,
            ]:
                return Response(
                    {"error": "Certains champs sont manquants."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            article_instance = get_object_or_404(article, pk=article_id)

            if article_instance.produit.statut == "en masse":
                response_data, status_code = self.process_mass_duplication(
                    article_instance,
                    quantity,
                    emplacement_id,
                    departement_id,
                    numero_serie,
                    personne,
                    tag_references,
                )
            else:
                response_data, status_code = self.process_single_duplication(
                    article_instance,
                    quantity,
                    emplacement_id,
                    departement_id,
                    numero_serie,
                    tag_references,
                    personne,
                )

            return Response(response_data, status=status_code)

        except article.DoesNotExist:
            return Response(
                {"error": "Article non trouvé."}, status=status.HTTP_404_NOT_FOUND
            )

        except ValueError as e:
            return Response(
                {"error": f"Erreur de valeur: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"error": f"Une erreur inattendue est survenue: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def process_mass_duplication(
        self,
        article_instance,
        quantity,
        emplacement_id,
        departement_id,
        numero_serie,
        personne,
        tag_references,
    ):
        # Vérifiez les références des tags
        for tag_reference in tag_references:
            try:
                tag_instance = tag.objects.get(reference=tag_reference)
            except tag.DoesNotExist:
                return {
                    "error": f"Le tag avec la référence {tag_reference} est inconnu."
                }, status.HTTP_404_NOT_FOUND

            # Vérifiez si le tag est déjà affecté
            if tag_instance.affecter:
                return {
                    "error": f"Le tag avec la référence {tag_reference} est déjà affecté. La duplication n'est pas autorisée."
                }, status.HTTP_400_BAD_REQUEST

        # Vérifiez la quantité reçue
        if article_instance.qte_recue is None or article_instance.qte_recue < quantity:
            return {
                "error": "La quantité demandée dépasse la quantité reçue de l'article."
            }, status.HTTP_400_BAD_REQUEST

        # Récupération de l'instance de la personne
        personne_instance = None
        if personne != -1 and personne != 0:
            personne_instance = Personne.objects.filter(id=personne).first()

        # Récupération des instances des départements et emplacements
        departement_instance = get_object_or_404(departement, id=departement_id)
        emplacement_instance = get_object_or_404(emplacement, id=emplacement_id)

        items = []
        for tag_reference in tag_references:
            tag_instance = get_object_or_404(tag, reference=tag_reference)

            # Créez un nouvel item
            new_item = item(
                statut="affecter",
                archive=False,
                emplacement=emplacement_instance,
                departement=departement_instance,
                article=article_instance,
                tag=tag_instance,
                date_affectation=timezone.now(),
                numero_serie=numero_serie,
                affectation_personne=personne_instance,
            )
            items.append(new_item)
            tag_instance.affecter = True
            tag_instance.save()
            article_instance.qte_recue -= quantity
            article_instance.save()

        # Utilisez bulk_create pour l'insertion en lot
        try:
            item.objects.bulk_create(items)
        except Exception as e:
            return {
                "error": f"Une erreur s'est produite lors de la création des items: {str(e)}"
            }, status.HTTP_500_INTERNAL_SERVER_ERROR

        return {
            "message": "Les articles ont été dupliqués avec succès."
        }, status.HTTP_201_CREATED

    def process_single_duplication(
        self,
        article_instance,
        quantity,
        emplacement_id,
        departement_id,
        numero_serie,
        tag_references,
        personne,
    ):
        if article_instance.qte_recue is None or article_instance.qte_recue < quantity:
            return {
                "error": "La quantité demandée dépasse la quantité reçue de l'article."
            }, status.HTTP_400_BAD_REQUEST
        if not tag_references:
            return {
                "error": "Au moins un tag est requis pour la création."
            }, status.HTTP_400_BAD_REQUEST
        if len(tag_references) > 1:
            return {
                "error": f" Au max un tag est requis pour la création"
            }, status.HTTP_400_BAD_REQUEST
        tag_reference = tag_references[0]
        if personne != -1 and personne != 0:
            personne_instance = Personne.objects.filter(id=personne).first()
        else:
            personne_instance = None
        try:
            departement_instance = departement.objects.filter(id=departement_id).first()
        except departement.DoesNotExist:
            return {
                "error": f"departement selectionner est incunnu."
            }, status.HTTP_404_NOT_FOUND
        try:
            emplacement_instance = emplacement.objects.filter(id=emplacement_id).first()
        except emplacement.DoesNotExist:
            return {
                "error": f"emplacement selectionner est incunnu."
            }, status.HTTP_404_NOT_FOUND

        try:
            tag_instance = tag.objects.get(reference=tag_reference)
        except tag.DoesNotExist:
            return {
                f"Le tag avec la référence {tag_reference} est incunnu."
            }, status.HTTP_404_NOT_FOUND

        if tag_instance.affecter:
            return {
                "error": f"Le tag avec la référence {tag_reference} est déjà affecté. La duplication n'est pas autorisée."
            }, status.HTTP_400_BAD_REQUEST
        new_item = item(
            statut="affecter",
            archive=False,
            emplacement=emplacement_instance,
            article=article_instance,
            departement=departement_instance,
            tag=tag_instance,
            date_affectation=timezone.now(),
            numero_serie=numero_serie,
            affectation_personne=personne_instance,
        )
        new_item.save()

        tag_instance.affecter = True
        tag_instance.save()
        article_instance.qte_recue -= quantity
        article_instance.save()
        return {"message": "L'article a été crée avec succès."}, status.HTTP_201_CREATED








class AnnulerAffectationAPIView(APIView):
    def post(self, request, item_id):
        try:
            with transaction.atomic():
                # Récupérer l'item
                item_instance = get_object_or_404(item, id=item_id)
                
                # Vérifier s'il y a un tag associé
                if item_instance.tag:
                    tag_instance = item_instance.tag
                    tag_instance.affecter = False
                    tag_instance.save()
                    
                # Mettre à jour la quantité reçue de l'article
                if item_instance.article:
                    item_instance.article.qte_recue = (item_instance.article.qte_recue or 0) + 1
                    item_instance.article.save()

                # Supprimer la relation entre l'item et le tag
                item_instance.tag = None
                item_instance.save()

                # Supprimer l'item
                item_instance.delete()

                return Response({"message": "Affectation annulée avec succès."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)





class ItemDetailsAPI(APIView):
    def calculate_residual_value(self, item_obj):
        """Calculate the residual value based on the item and its related article."""
        if not item_obj.article:
            return None  # If there's no related article, return None

        # Extracting required fields
        duree_amortissement = item_obj.article.produit.duree_amourtissement
        prix_achat = item_obj.article.prix_achat

        if duree_amortissement is None or prix_achat is None:
            return None  # If either value is missing, return None

        # Calculate the depreciation rate (taut)
        taut = (100 / duree_amortissement) / 100  # Convert to a percentage

        # Calculate the annual depreciation amount (va)
        va = taut * prix_achat

        # Calculate the number of years since purchase
        current_year = datetime.now().year
        purchase_year = item_obj.article.date_achat.year
        annee = current_year - purchase_year

        # Conditions for calculating residual value
        if annee > duree_amortissement:
            # If the item has been depreciated for longer than its useful life
            valeur_residuelle = prix_achat - (va * duree_amortissement)
        else:
            # If the item is within its useful life
            valeur_residuelle = prix_achat - (va * annee)

        # Ensure the residual value is not negative
        return max(valeur_residuelle, 0)

    def get(self, request):
        try:
            user = request.user
            # Récupérer le paramètre de requête 'tag_reference'
            tag_reference = request.query_params.get("tag_reference", None)
            print("tag_reference")
            print(tag_reference)
            # Filtrer les objets en fonction du tag si 'tag_reference' est fourni
            if tag_reference:
                item_obj = (
                    item.objects.select_related(
                        "article", "tag", "emplacement", "departement"
                    )
                    .filter(tag__reference=tag_reference, tag__compte=user.compte)
                    .first()
                )
                if not item_obj:
                    return Response(
                        {"error": "Aucun élément trouvé pour ce tag."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                return Response(
                    {"error": "Veuillez fournir un tag."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Calculate the residual value
            valeur_residuelle = self.calculate_residual_value(item_obj)

            # Construction de la réponse
            response_data = {
                "id": item_obj.id,
                "statut": item_obj.statut,
                "date_affectation": item_obj.date_affectation,
                "personne": (
                    f"{item_obj.affectation_personne.nom} {item_obj.affectation_personne.prenom}"
                    if item_obj.affectation_personne
                    else None
                ),
                "reference": item_obj.reference_auto,
                "numero_serie": item_obj.numero_serie,
                "departement": (
                    item_obj.departement.nom if item_obj.departement else None
                ),
                "emplacement": (
                    item_obj.emplacement.nom if item_obj.emplacement else None
                ),
                "tag": item_obj.tag.reference if item_obj.tag else None,
                "archive": item_obj.archive,
                "codeArticle": item_obj.article.code_article,
                "designation": item_obj.article.designation,
                "date_achat": item_obj.article.date_achat,
                "date_reception": item_obj.article.date_reception.date(),
                "numero_comptable": item_obj.article.numero_comptable,
                "couleur": item_obj.article.couleur,
                "poids": item_obj.article.poids,
                "volume": item_obj.article.volume,
                "langueur": item_obj.article.langueur,
                "hauteur": item_obj.article.hauteur,
                "largeur": item_obj.article.largeur,
                "date_expiration": item_obj.article.date_expiration,
                "prix_achat": item_obj.article.prix_achat,
                "qte": item_obj.article.qte,
                "n_facture": item_obj.article.N_facture,
                "produit": (
                    item_obj.article.produit.libelle
                    if item_obj.article.produit
                    else None
                ),
                "marque": (
                    item_obj.article.marque.nom if item_obj.article.marque else None
                ),
                "fournisseur": (
                    item_obj.article.fournisseur.nom
                    if item_obj.article.fournisseur
                    else None
                ),
                "nature": (
                    item_obj.article.nature.libelle if item_obj.article.nature else None
                ),
                "categorie": (
                    item_obj.article.produit.categorie.libelle
                    if item_obj.article.produit.categorie
                    else None
                ),
                "valeur_residuelle": valeur_residuelle,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except item.DoesNotExist:
            return Response(
                {"error": "Aucun élément trouvé pour la référence du tag fournie."},
                status=status.HTTP_404_NOT_FOUND,
            )


class CreateDetailInventaireView(APIView):
    def post(self, request):
        data = request.data
        inventaire_id = data.get("inventaire_id")
        emplacement_id = data.get("emplacementId")
        print(request.data)
        list_detail = data.get("listDetail", [])

        # Récupérer les instances de l'inventaire et de l'emplacement
        try:
            inventaire_instance = inventaire.objects.get(pk=inventaire_id)
            emplacement_instance = emplacement.objects.get(pk=emplacement_id)
        except inventaire.DoesNotExist:
            return Response(
                {"error": "Inventaire non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )

        # Essayer de trouver l'instance inventaire_emplacement
        inventaire_emplacement_instance = inventaire_emplacement.objects.filter(
            inventaire=inventaire_instance, emplacement=emplacement_instance
        ).first()

        if not inventaire_emplacement_instance:
            return Response(
                {"error": "Inventaire emplacement non trouvé"},
                status=status.HTTP_404_NOT_FOUND,
            )

        erreurs = []

        # Boucle à travers les détails
        for detail in list_detail:
            item_id = detail.get("item_id")
            statut = detail.get("statut")

            try:
                print(inventaire_emplacement_instance.id)

                # Préparer les données pour le sérialiseur
                detail_data = {
                    "inventaire_emplacement": inventaire_emplacement_instance.id,
                    "item": item_id,
                    "etat": statut,
                }
                print(detail_data)

                # Valider et enregistrer le détail de l'inventaire
                serializer = CreatDetailInventaireSerializer(data=detail_data)
                print(serializer.is_valid())
                if serializer.is_valid():
                    serializer.save()
                else:
                    erreurs.append(serializer.errors)

            except item.DoesNotExist:
                erreurs.append({"error": f"Item avec l'ID {item_id} non trouvé"})
            except Exception as e:
                erreurs.append({"error": str(e)})
        inventaire_emplacement_instance.statut = "Terminer"
        inventaire_emplacement_instance.save()
        inventaire_instance.lancer_inventaire(inventaire_id)

        return Response(
            {"message": "Détail inventaire créé avec succès", "errors": erreurs},
            status=status.HTTP_201_CREATED,
        )


def get_detail_inventaire_by_compte(user):
    if user.is_authenticated:
        compte = user.compte

        # Faire la jointure avec inventaire et Compte via UserWeb
        queryset = detail_inventaire.objects.filter(inventaire__user__compte=compte)

        return queryset
    else:
        return None


import logging


class DetailInventaireListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les détails d'inventaire avec support DataTable et Export Excel
    """
    model = detail_inventaire
    serializer_class = DetailInventairesSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'detail_inventaire'
    
    
    # Configuration DataTable
    search_fields = [
        'etat',
        'id',
        'item__article__designation',
        'item__reference_auto',
        'inventaire_emplacement__emplacement__nom',
        'item__affectation_personne__nom',
        'item__affectation_personne__prenom'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'etat',
        'item__article__designation',
        'inventaire_emplacement__emplacement__nom',
        'inventaire_emplacement__start_at',
        'created_at'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 10
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'etat': 'etat',
        'start_at': 'inventaire_emplacement__start_at',
        'item_designation': 'item__article__designation',
        'emplacement': 'inventaire_emplacement__emplacement__nom',
        'reference': 'item__reference_auto',
        'created_at': 'created_at'
    }

    def get_datatable_queryset(self):
        """Queryset de base filtré par inventaire_id"""
        inventaire_id = self.kwargs.get('inventaire_id')
        
        if not self.request.user.compte:
            return detail_inventaire.objects.none()
        
        try:
            inventaire_instance = inventaire.objects.get(pk=inventaire_id)
            inventaire_emplacement_instance = inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            ).values_list("id", flat=True)
            
            return detail_inventaire.objects.filter(
                inventaire_emplacement__in=inventaire_emplacement_instance,
                inventaire_emplacement__inventaire__user__compte=self.request.user.compte
            ).select_related(
                'item',
                'item__article',
                'item__article__produit',
                'item__article__produit__categorie',
                'item__emplacement',
                'item__departement',
                'item__affectation_personne',
                'item__tag',
                'inventaire_emplacement',
                'inventaire_emplacement__emplacement'
            ).order_by('-created_at')
        except inventaire.DoesNotExist:
            return detail_inventaire.objects.none()
    
    
    def calculate_residual_value(self, item_obj):

        if not item_obj.article:
            return None

        duree_amortissement = item_obj.article.produit.duree_amourtissement
        prix_achat = item_obj.article.prix_achat

        if duree_amortissement is None or prix_achat is None:
            return None  # If either value is missing, return None

        taut = (100 / duree_amortissement) / 100

        # Calculate the annual depreciation amount (va)
        va = taut * prix_achat

        # Calculate the number of years since purchase
        current_year = datetime.now().year
        purchase_year = item_obj.article.date_achat.year
        annee = current_year - purchase_year

        # Conditions for calculating residual value
        if annee > duree_amortissement:
            # If the item has been depreciated for longer than its useful life
            valeur_residuelle = prix_achat - (va * duree_amortissement)
        else:
            # If the item is within its useful life
            valeur_residuelle = prix_achat - (va * annee)

        # Ensure the residual value is not negative
        return max(valeur_residuelle, 0)



class ArchiverItemAPIView(APIView):
    def post(self, request):
        # Données d'entrée
        item_id = request.data.get("id")
        commentaire = request.data.get("commentaire")
        action = request.data.get("action")

        # Validation basique
        if not item_id:
            return Response(
                {"error": "id item not provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not action:
            return Response(
                {"error": "Action not provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = archive_or_unarchive_item_service(
                item_id=int(item_id), action=action, commentaire=commentaire
            )
        except item.DoesNotExist:
            return Response(
                {"error": "Item not found for this id"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "message": result.message,
                "already_archived": result.already_archived,
            },
            status=status.HTTP_200_OK,
        )


class ArchiveItemBatchAPIView(APIView):
    """
    API batch pour archiver plusieurs items en une seule requête.

    Body attendu (JSON) :
    {
        "items_id": [1, 2, 3]
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ArchiveItemBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items_id = serializer.validated_data["items_id"]

        try:
            result = archive_items_batch_service(
                user=request.user,
                items_id=items_id,
            )
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result, status=status.HTTP_200_OK)



class ArchiveItemExcelImportAPIView(APIView):
    """
    API pour importer un fichier Excel et archiver des items en masse.

    Le fichier doit contenir au moins une colonne 'id' (ID de l'item) et
    optionnellement une colonne 'commentaire'.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ArchiveItemExcelImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        excel_file = serializer.validated_data["file"]
        skip_errors = serializer.validated_data["skip_errors"]

        try:
            result = import_archive_items_from_excel_service(
                user=request.user, excel_file=excel_file, skip_errors=skip_errors
            )
        except ArchiveItemsImportError as exc:
            # Tout ou rien : aucune ligne archivée si des erreurs sont présentes
            return Response({"errors": exc.errors}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result, status=status.HTTP_200_OK)


class operationsListAPIView(APIView):
    def get(self, request):
        operations = operation.objects.all()
        serializer = OperationSerializer(operations, many=True)
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddOperationItemView(APIView):
    def post(self, request):
        data = request.data
        print(data)
        try:
            tag_instance = tag.objects.get(reference=data["tag_reference"])
        except tag.DoesNotExist:
            return Response(
                {"error": "Tag not found"}, status=status.HTTP_404_NOT_FOUND
            )
        # Find the item related to the tag
        try:
            item_instance = item.objects.get(tag=tag_instance)
        except item.DoesNotExist:
            return Response(
                {"error": "Item not found for the given tag"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get the operation based on the ID received in the request
        try:
            operation_instance = operation.objects.get(id=data["operation_id"])
        except operation.DoesNotExist:
            return Response(
                {"error": "Operation not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Create the new operation_article entry
        serializer = OperationItemSerializer(
            data={
                "item": item_instance.id,
                "operation": operation_instance.id,
                "prix": data.get("prix"),  # Prix de l'opération
                "date_operation": data.get("date_operation"),  # Date de l'opération
                "attachement": request.FILES.get(
                    "attachement"
                ),  # Use request.FILES for file uploads
                "commentaire": data.get("commentaire"),  # This can be a comment or null
            }
        )

        # Validate and save the operation_article instance
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "operation added successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OperationItemListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les opérations d'un item avec support DataTable
    
    Fonctionnalités automatiques :
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés
    - Export Excel/CSV
    """
    model = operation_article
    serializer_class = OperationItemsSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'operations_item'
    
    # Configuration DataTable
    search_fields = [
        'operation__reference',
        'item__article__designation',
        'item__reference_auto',
        'commentaire'
    ]
    
    order_fields = [
        'id',
        'operation__reference',
        'item__article__designation',
        'created_at',
        'commentaire'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 10
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des filtres
    filter_aliases = {
        'id': 'id',
        'operation_reference': 'operation__reference',
        'item_designation': 'item__article__designation',
        'item_reference': 'item__reference_auto',
        'commentaire': 'commentaire',
        'created_at': 'created_at'
    }

    def get_datatable_queryset(self):
        """Queryset de base - opérations d'un item spécifique"""
        item_id = self.kwargs.get('item_id')
        
        if not item_id:
            return operation_article.objects.none()
        
        try:
            item_instance = item.objects.get(pk=item_id)
            
            if not self.request.user.compte:
                return operation_article.objects.none()
            
            return operation_article.objects.filter(
                item__article__compte=self.request.user.compte,
                item=item_instance
            ).select_related(
                'operation',
                'item',
                'item__article',
                'item__tag'
            ).order_by('-created_at')
            
        except item.DoesNotExist:
            return operation_article.objects.none()
    
    def get(self, request, item_id, *args, **kwargs):
        """Override pour passer item_id au queryset"""
        self.kwargs['item_id'] = item_id
        return super().get(request, *args, **kwargs)


class InventaireEmplacementCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, inventaire_id, format=None):
        try:
            print(inventaire_id)
            inventaire_instance = inventaire.objects.get(id=inventaire_id)

            # Récupérer tous les emplacements associés à cet inventaire
            emplacements = inventaire_emplacement.objects.filter(
                inventaire=inventaire_instance
            )

            # Compter le nombre total d'emplacements
            total_emplacements = emplacements.count()

            # Compter le nombre d'emplacements avec le statut "Terminer"
            emplacements_terminer = emplacements.filter(statut="Terminer").count()
            print()
            # Retourner le résultat dans la réponse
            data = {
                "total_emplacements": total_emplacements,
                "emplacements_terminer": emplacements_terminer,
            }

            return Response(data, status=status.HTTP_200_OK)

        except inventaire.DoesNotExist:
            # Si l'inventaire n'existe pas, renvoyer une erreur 404
            return Response(
                {"error": "Inventaire not found"}, status=status.HTTP_404_NOT_FOUND
            )


class UpdateTagAPIView(APIView):
    def post(self, request, *args, **kwargs):

        old_tag_id = request.data.get("old_tag_id")
        new_tag_id = request.data.get("new_tag_id")
        print(request.data)
        user_id = request.user.id
        try:
            old_tag = tag.objects.filter(reference=old_tag_id).first()
        except tag.DoesNotExist:
            return Response(
                {"error": "tag l’ancien non trouvé."}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            new_tag = tag.objects.filter(reference=new_tag_id).first()
        except tag.DoesNotExist:
            return Response(
                {"error": "nouveau tag non trouvé."}, status=status.HTTP_404_NOT_FOUND
            )

        # Récupérer l'utilisateur qui effectue l'action
        user_instance = get_object_or_404(UserWeb, id=user_id)
        # Récupérer l'item associé à l'ancien tag
        try:
            item_instance = item.objects.get(tag=old_tag)
        except item.DoesNotExist:
            return Response(
                {"error": "Item associé à l’ancien tag non trouvé."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Créer une entrée dans TagHistory en passant les instances des objets
        old_tag.affecter = False
        old_tag.statut = "off"
        old_tag.save()
        TagHistory.objects.create(
            item=item_instance,
            old_tag=old_tag,  # Passer l'instance du tag
            new_tag=new_tag,  # Passer l'instance du tag
            changed_by=user_instance,  # Passer l'instance de l'utilisateur
        )

        # Mettre à jour le tag de l'item
        item_instance.tag = new_tag  # Assigner l'instance du tag
        item_instance.save()

        return Response(
            {"message": "Tag mis à jour avec succès."}, status=status.HTTP_200_OK
        )


class UpdateStartAtAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            print("="*70)
            print("📥 UpdateStartAtAPIView - Request received")
            print(f"Request data type: {type(request.data)}")
            print(f"Request data: {request.data}")
            
            # Gérer le cas où request.data est une liste directement
            if isinstance(request.data, list):
                ids = request.data
            else:
                # Gérer le cas où request.data est un dictionnaire
                ids = request.data.get("ids", [])
            
            print(f"IDs extracted: {ids}")
            
            if not ids:
                return Response(
                    {"error": "No IDs provided."}, status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier que les objets existent avant la mise à jour
            existing_objects = inventaire_emplacement.objects.filter(id__in=ids)
            existing_count = existing_objects.count()
            print(f"✅ Found {existing_count} inventaire_emplacement objects with IDs: {ids}")
            
            # Afficher l'état AVANT la mise à jour
            print("\n📊 État AVANT mise à jour:")
            for obj in existing_objects:
                print(f"   ID: {obj.id} | start_at: {obj.start_at} | statut: {obj.statut}")
            
            # Mettre à jour les emplacements d'inventaire
            updated_count = existing_objects.update(start_at=True)
            print(f"\n🔄 Nombre d'objets mis à jour: {updated_count}")
            
            # Afficher l'état APRÈS la mise à jour
            print("\n📊 État APRÈS mise à jour:")
            updated_objects = inventaire_emplacement.objects.filter(id__in=ids)
            for obj in updated_objects:
                print(f"   ID: {obj.id} | start_at: {obj.start_at} | statut: {obj.statut}")
            
            print("="*70)
            
            return Response(
                {
                    "message": "Inventaire updated successfully.",
                    "updated_count": updated_count,
                    "found_count": existing_count
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            print(f"❌ Error in UpdateStartAtAPIView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticlesConsommesListAPIView(ServerSideDataTableView):
    """
    Vue pour lister les articles consommés (qte_recue=0) avec support DataTable
    
    Fonctionnalités automatiques via @datatables/:
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés avec mapping automatique
    - Gestion d'erreurs
    - Support DataTable + REST API + Export Excel
    """
    model = article
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'articles_consommes'
    
    
    # Configuration DataTable
    search_fields = [
        'id',
        'code_article',
        'designation',
        'numero_comptable',
        'N_facture',
        'produit__libelle',
        'fournisseur__nom',
        'produit__categorie__libelle'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'designation',
        'date_achat',
        'qte',
        'N_facture',
        'code_article',
        'prix_achat'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 20
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'designation': 'designation',
        'code_article': 'code_article',
        'date_achat': 'date_achat',
        'date_reception': 'date_reception',
        'qte': 'qte',
        'qte_recue': 'qte_recue',
        'N_facture': 'N_facture',
        'prix_achat': 'prix_achat'
    }

    def get_datatable_queryset(self):
        """
        Queryset de base avec filtres métier.
        Seuls les articles consommés (qte_recue=0) sont retournés.
        """
        if not self.request.user.compte:
            return article.objects.none()
            
        return article.objects.filter(
            compte=self.request.user.compte,
            qte_recue=0
        ).select_related(
            'produit',
            'produit__categorie',
            'fournisseur',
            'marque',
            'nature'
        ).order_by("-id")
    

class TagHistoryListAPIView(ServerSideDataTableView):
    """
    Vue pour lister l'historique des changements de tags d'un item avec support DataTable
    
    Fonctionnalités automatiques :
    - Pagination côté serveur
    - Recherche globale et par colonnes
    - Tri multi-colonnes
    - Filtres avancés
    - Export Excel/CSV
    """
    model = TagHistory
    serializer_class = TagHistorySerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'tag_history'
    
    # Configuration DataTable
    search_fields = [
        'old_tag__reference',
        'new_tag__reference',
        'item__article__designation',
        'item__reference_auto',
        'changed_by__nom',
        'changed_by__prenom'
    ]
    
    order_fields = [
        'id',
        'old_tag__reference',
        'new_tag__reference',
        'created_at'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 10
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des filtres
    filter_aliases = {
        'id': 'id',
        'old_tag': 'old_tag__reference',
        'new_tag': 'new_tag__reference',
        'item_designation': 'item__article__designation',
        'item_reference': 'item__reference_auto',
        'changed_by': 'changed_by__nom',
        'created_at': 'created_at'
    }

    def get_datatable_queryset(self):
        """Queryset de base - historique d'un item spécifique"""
        item_id = self.kwargs.get('item_id')
        
        if not item_id:
            return TagHistory.objects.none()
            
        return TagHistory.objects.filter(
            item__id=item_id
        ).select_related(
            'item',
            'item__article',
            'old_tag',
            'new_tag',
            'changed_by'
        ).order_by('-created_at')
    
    def get(self, request, item_id, *args, **kwargs):
        """Override pour passer item_id au queryset"""
        self.kwargs['item_id'] = item_id
        return super().get(request, *args, **kwargs)


class ArticleExportExcelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return all articles; vous pouvez modifier cette partie si nécessaire
        authenticated_user = self.request.user
        return article.objects.filter(qte_recue__gt=0).order_by("id")

    def filter_queryset(self, qs):
        search = self.request.GET.get("search[value]", None)
        ordering = self.request.GET.get("ordering", "id")
        if search:
            qs = qs.filter(
                Q(code_article__istartswith=search) | Q(designation__icontains=search)
            )
        qs = qs.order_by(ordering)
        return qs

    def get(self, request, *args, **kwargs):
        # Récupérer et filtrer les articles
        qs = self.get_queryset()
        filtered_qs = self.filter_queryset(qs)

        # Préparer les données pour l'exportation Excel
        data = filtered_qs.values(
            "code_article",
            "designation",
            "date_achat",
            "numero_comptable",
            "couleur",
            "poids",
            "volume",
            "langueur",
            "hauteur",
            "largeur",
            "prix_achat",
            "qte_recue",
        )

        # Utiliser pandas pour créer le DataFrame et exporter vers Excel
        df = pd.DataFrame(list(data))

        # Créer la réponse HTTP avec le fichier Excel
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=articles_filtered.xlsx"

        # Exporter les données dans le fichier Excel
        df.to_excel(response, index=False)

        return response


class AffecterTagEmplacementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TagAffectationSerializer(data=request.data)
        if serializer.is_valid():
            emplacement_instance = serializer.validated_data["emplacement_instance"]
            tag_instance = serializer.validated_data["tag_instance"]

            # Affecter le tag à l'emplacement
            emplacement_instance.tag = tag_instance
            emplacement_instance.save()
            print(tag_instance)
            # Marquer le tag comme affecté
            tag_instance.affecter = True
            tag_instance.save()

            return Response(
                {"message": "Tag affecté à l'emplacement avec succès."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CountItemPerEmplacement(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, emplacement_id):
        try:
            # Compte les articles pour un emplacement donné
            item_count = item.objects.filter(emplacement__id=emplacement_id).count()
            # Retourne le nombre d'articles dans la réponse
            return Response({"item_count": item_count}, status=status.HTTP_200_OK)
        except item.DoesNotExist:
            # Gérer le cas où l'emplacement n'existe pas
            return Response(
                {"error": "Emplacement non trouvé"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Gérer d'autres exceptions générales
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Récupérer tous les groupes auxquels l'utilisateur appartient
        groups = user.groups.all()

        # Initialiser une liste pour la réponse
        permissions_list = []

        # Parcourir chaque groupe et récupérer ses permissions
        for group in groups:
            permissions = group.permissions.all()
            group_permissions = [f"{perm.codename}" for perm in permissions]
            permissions_list.extend(group_permissions)

        # Supprimer les doublons
        permissions_list = list(set(permissions_list))

        return Response({"permissions": permissions_list})


# =============================================================================
# VUES DATATABLES - Nouvelles vues avec intégration du package datatables
# =============================================================================



class TransferHistoriqueListView(ServerSideDataTableView):
    """
    Vue pour lister l'historique des transferts d'un item avec support DataTable
    """
    model = TransferHistorique
    serializer_class = TransferHistoriqueSerializer
    permission_classes = [IsAuthenticated]
    
    # Configuration de l'export (activé par défaut)
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'transferts_historique'
    
    
    # Configuration DataTable
    search_fields = [
        'item_transfer__article__designation',
        'item_transfer__reference_auto',
        'new_emplacement__nom',
        'old_emplacement__nom',
        'new_departement__nom',
        'old_departement__nom'
    ]
    
    # Champs pour le tri
    ordering_fields = [
        'id',
        'item_transfer__reference_auto',
        'created_at',
        'new_emplacement__nom',
        'old_emplacement__nom'
    ]
    
    # Configuration de pagination
    default_order = '-created_at'
    page_size = 10
    min_page_size = 1
    max_page_size = 100
    
    # Mapping des champs frontend vers backend
    filter_aliases = {
        'id': 'id',
        'item_reference': 'item_transfer__reference_auto',
        'item_designation': 'item_transfer__article__designation',
        'new_emplacement': 'new_emplacement__nom',
        'old_emplacement': 'old_emplacement__nom',
        'new_departement': 'new_departement__nom',
        'old_departement': 'old_departement__nom',
        'created_at': 'created_at'
    }

    def get_datatable_queryset(self):
        """Queryset de base - historique d'un item spécifique"""
        item_id = self.kwargs.get('item_transfer')
        
        if not item_id:
            return TransferHistorique.objects.none()
            
        return TransferHistorique.objects.filter(
            item_transfer=item_id
        ).select_related(
            'item_transfer',
            'item_transfer__article',
            'new_emplacement',
            'old_emplacement',
            'new_personne',
            'old_personne',
            'new_departement',
            'old_departement'
        ).order_by("id")


class AssignTagToEmplacementAPIView(APIView):
    def post(self, request):
        # Récupérer les données du corps de la requête
        emplacement_id = request.data.get("emplacement_id")
        tag_reference = request.data.get("tag_reference")

        # Vérifier que les données requises sont présentes
        if not emplacement_id:
            return Response(
                {"error": "Emplacement ID not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not tag_reference:
            return Response(
                {"error": "Tag reference not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Récupérer l'emplacement
            emplacement_instance = emplacement.objects.get(pk=emplacement_id)
        except emplacement.DoesNotExist:
            return Response(
                {"error": "Emplacement not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Récupérer le tag
            tag_instance = tagEmplacement.objects.get(reference=tag_reference)
        except tagEmplacement.DoesNotExist:
            return Response(
                {"error": "Tag not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Vérifier si l'emplacement a déjà un tag
        if emplacement_instance.tag:
            return Response(
                {"error": "This emplacement already has a tag assigned"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Assigner le tag à l'emplacement
        emplacement_instance.tag = tag_instance
        emplacement_instance.save()

        return Response(
            {"message": "Tag successfully assigned to emplacement"},
            status=status.HTTP_200_OK,
        )
