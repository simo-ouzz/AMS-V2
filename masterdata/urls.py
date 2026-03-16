"""
URLs Configuration pour l'application MasterData

Ce fichier définit toutes les routes de l'API pour le système de gestion d'actifs (AMS).
Il organise les endpoints par fonctionnalité et utilise les vues basées sur les classes Django REST Framework.

ARCHITECTURE:
- Authentification JWT : Login, tokens, permissions
- Données de référence : Départements, emplacements, produits, etc.
- Articles et Items : Gestion des articles et de leurs instances
- Inventaires : Gestion des inventaires par emplacement, zone, location, département
- Opérations : Affectation, transfert, archivage, maintenance
- KPIs et Dashboard : Statistiques et indicateurs de performance
- Mobile API : Endpoints spécialisés pour l'application mobile

CONVENTIONS:
- URLs REST : /resource/action/ ou /resource/id/action/
- Noms des patterns : resource-action ou resource_action
- Support des filtres avancés via query parameters
- Pagination automatique pour les listes
- Format de réponse JSON standardisé
"""

from django.urls import path
from django.views.i18n import set_language

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)

from django.conf import settings
from django.conf.urls.static import static


from masterdata.Views.DashboardView import (
    AmortizationCountView,
    ArchivedItemsCountView,
    ArticleCountView,
    CategorieItemCountView,
    DepartementListView,
    FinancialValueByDepartmentView,
    GlobalResidualValueAPIView,
    ItemsCountCountView,
    LocationListAPIView,
    PersonneItemSummaryListView,
    ResidualValueByCategoryAPIView,
    ResidualValueGlobalCurrentYearView,
    TagsCountCountView,
    TypeTagCountCountView,
)
from masterdata.Views.KPIDashboardAPI import KPIDashboardAPIView
from masterdata.Views.KPIIndividualEndpoints import (
    TotalArticlesAPIView,
    ArticlesParFournisseurAPIView,
    ArticlesParFamilleAPIView,
    ArticlesParCategorieAPIView,
    ArticlesParNatureAPIView,
    TotalTransfertsAPIView,
    ValeurTotaleAchatsAPIView,
    ValeurParFournisseurAPIView,
    TauxAffectationAPIView,
    ValeurResiduelleTotaleAPIView,
    ItemsParDepartementAPIView,
    TotalItemsAPIView,
    ItemsArchivesAPIView,
    TotalEmplacementsAPIView,
    TotalLocationsAPIView,
    TotalZonesAPIView,
    TagsAffectationAPIView,
)
from masterdata.views import (
    AddOperationItemView,
    AffecterTagEmplacementView,
    AnnulerAffectationAPIView,
    ArchiveItemBatchAPIView,
    ArchiveItemExcelImportAPIView,
    ArchiveItemListAPIView,
    ArchiverItemAPIView,
    ArticleCreateAPIView,
    ArticleDeleteAPIView,
    ArticleExportExcelAPIView,
    ArticleImportAPIView,
    ArticlesListAPIView,
    ArticleUpdateAPIView,
    ArticlesConsommesListAPIView,
    AssignTagToEmplacementAPIView,
    CategoriesListAPIView,
    CountItemPerEmplacement,
    CreateDetailInventaireView,
    DetailInventaireListAPIView,
    DuplicationView,
    EditArticleAPIView,
    EditItemAPIView,
    EmplacementsMobileListAPIView,
    InfoInventaire,
    InventaireCreateByDepartementAPIView,
    InventaireDepartementDetailAPIView,
    InventaireDepartementListAPIView,
    InventaireDepartementUpdateAPIView,
    InventaireEmplacementCountAPIView,
    InventaireEmplacementCreateAPIView,
    ItemUpdateAPIView,
    LocationsMobileListAPIView,
    TagHistoryListAPIView,
    TransferHistoriqueListView,
    UpdateTagAPIView,
    InventaireEmplacementDetailAPIView,
    InventaireEmplacementListAPIView,
    InventaireEmplacementListMobileAPIView,
    InventaireEmplacementUpdateAPIView,
    InventaireEmplacementsDetailAPIView,
    InventaireLocationCreateAPIView,
    InventaireLocationDetailAPIView,
    InventaireLocationListsAPIView,
    InventaireLocationUpdateAPIView,
    InventaireZoneCreateAPIView,
    InventaireZoneDetailsAPIView,
    InventaireZoneListsAPIView,
    InventaireZoneUpdatesAPIView,
    ItemDetailsAPI,
    ItemListAPIView,
    LoginUserView,
    MobileArticleListAPIView,
    ModifierStatutInventaireEmplacement,
    OperationItemListAPIView,
    PersonnesListAPIView,
    TagCreateView,
    TypeTagsListAPIView,
    UpdateArticleEmplacement,
    UpdateQteRecueView,
    UpdateStartAtAPIView,
    UserDetailAPIView,
    UserPermissionsView,
    ValidateArticleView,
    VerifyTagsLocationAPI,
    VerifyTagsNonPlanifierAPI,
    ZonesMobileListAPIView,
    assign_groups_view,
    departementsListAPIView,
    emplacementsListAPIView,
    fournisseursListAPIView,
    locationsListAPIView,
    marquesListAPIView,
    naturesListAPIView,
    operationsListAPIView,
    produitsListAPIView,
    tagsListAPIView,
    zonesListAPIView,
    zonesListFilterAPIView,
)


urlpatterns = [
    # =============================================================================
    # AUTHENTIFICATION ET AUTORISATION
    # =============================================================================
    
    # Authentification
    path("login/mobile/", LoginUserView.as_view(), name="login"),  # POST - Login mobile
    
    # Gestion des tokens JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),  # POST - Obtenir token
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),  # POST - Rafraîchir token
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),  # POST - Vérifier token
    path("api/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),  # POST - Blacklist token
    
    # Utilisateur et permissions
    path("detail/user/", UserDetailAPIView.as_view(), name="user-detail"),  # GET - Info utilisateur
    path('user/permissions/', UserPermissionsView.as_view(), name='user-permissions'),  # GET - Permissions utilisateur
    path('assign-groups/', assign_groups_view, name='assign-groups'),  # POST - Assigner groupes
    
    # =============================================================================
    # DONNÉES DE RÉFÉRENCE (Master Data) - Listes de base
    # =============================================================================

    # Organisation
    path("departements/all_departement/", departementsListAPIView.as_view(), name="departements-list"),  # GET - Liste départements
    path("personnes/all_personne/", PersonnesListAPIView.as_view(), name="personne-list"),  # GET - Liste personnes
    
    # Géolocalisation (hiérarchie: Location > Zone > Emplacement)
    path("locations/all_location/", locationsListAPIView.as_view(), name="locations-list"),  # GET - Liste locations
    path("zones/all_zone/", zonesListAPIView.as_view(), name="zones-list"),  # GET - Liste zones
    path("zones/location/", zonesListFilterAPIView.as_view(), name="zones-list-filter"),  # GET - Zones par location
    path("emplacements/all_emplacement/", emplacementsListAPIView.as_view(), name="emplacements-list"),  # GET - Liste emplacements
    
    # Classification produits
    path("categories/all_categorie/", CategoriesListAPIView.as_view(), name="categories-list"),  # GET - Liste catégories
    path("produits/all_produit/", produitsListAPIView.as_view(), name="produits-list"),  # GET - Liste produits
    path("natures/all_nature/", naturesListAPIView.as_view(), name="natures-list"),  # GET - Liste natures
    path("marques/all_marque/", marquesListAPIView.as_view(), name="marques-list"),  # GET - Liste marques
    path("fournisseurs/all_fournisseur/", fournisseursListAPIView.as_view(), name="fournisseurs-list"),  # GET - Liste fournisseurs
    
    # Tags RFID
    path("tags/all_tag/", tagsListAPIView.as_view(), name="tags-list"),  # GET - Liste tags
    path("api/type-tag/", TypeTagsListAPIView.as_view(), name="type-tag"),  # GET - Liste types de tags
    path("tag/create/", TagCreateView.as_view(), name="tag-create"),  # POST - Créer tag
    path("item/update-tag/", UpdateTagAPIView.as_view(), name="update-tag"),  # PUT - Mettre à jour tag d'un item
    path("tag/all_Tag_History/<int:item_id>/", TagHistoryListAPIView.as_view(), name="tag-history-list"),  # GET - Historique tags d'un item (DataTable)
    path('assign-tag/', AssignTagToEmplacementAPIView.as_view(), name='assign-tag'),  # POST - Assigner tag à emplacement
    path("tag/affecter-tag-emplacement/", AffecterTagEmplacementView.as_view(), name="affecter-tag-emplacement"),  # POST - Affecter tag emplacement
    
    # =============================================================================
    # API MOBILE - Endpoints optimisés pour l'application mobile
    # =============================================================================
    
    path("mobile/all_location/", LocationsMobileListAPIView.as_view(), name="mobile-locations-list"),  # GET - Liste locations (mobile)
    path("mobile/zones/", ZonesMobileListAPIView.as_view(), name="mobile-zones-list"),  # GET - Liste zones (mobile)
    path("mobile/emplacements/", EmplacementsMobileListAPIView.as_view(), name="mobile-emplacements-list"),  # GET - Liste emplacements (mobile)
    path("mobile/article/all_articles/", MobileArticleListAPIView.as_view(), name="mobile-article-list"),  # GET - Liste articles (mobile)
    path("mobiel/inventaire/all_inventaire/", InventaireEmplacementListMobileAPIView.as_view(), name="mobile-inventaires-list"),  # GET - Liste inventaires (mobile)
    path('mobile/items/count/emplacement/<int:emplacement_id>/', CountItemPerEmplacement.as_view(), name='mobile-count-item-emplacement'),  # GET - Count items par emplacement
    
    # =============================================================================
    # ARTICLES - Gestion des articles et produits (DataTable)
    # =============================================================================
    
    # Listes d'articles (DataTable + filtres avancés + export Excel)
    path("article/all_article/", ArticlesListAPIView.as_view(), name="article-list"),  # GET - Liste articles (DataTable)
    path("article/all_articles/", ArticlesListAPIView.as_view(), name="article-list-full"),  # GET - Liste articles (DataTable)
    path("article/all_articles_Consommes/", ArticlesConsommesListAPIView.as_view(), name="article-consommes-list"),  # GET - Articles consommés qte_recue=0 (DataTable + Excel)
    
    # CRUD Articles
    path("article/create/", ArticleCreateAPIView.as_view(), name="article-create"),  # POST - Créer article
    path("article/get_article/<int:article_id>/", EditArticleAPIView.as_view(), name="get-article"),  # GET - Détails article
    path("article/update_article/<int:article_id>/", ArticleUpdateAPIView.as_view(), name="article-update"),  # PUT - Mettre à jour article
    path("article/supprimer/<int:id_article>/", ArticleDeleteAPIView.as_view(), name="article-delete"),  # DELETE - Supprimer article
    
    # Opérations spéciales articles
    path("article/import/", ArticleImportAPIView.as_view(), name="article-import"),  # POST - Importer articles (CSV/Excel)
    path("article/export/", ArticleExportExcelAPIView.as_view(), name="article-export-excel"),  # GET - Exporter articles Excel
    path("articles/update-qte-recue/<int:id_article>/", UpdateQteRecueView.as_view(), name="update-qte-recue"),  # PUT - Mettre à jour quantité reçue
    path("article/validate/<int:id_article>/", ValidateArticleView.as_view(), name="validate-article"),  # POST - Valider article
    path("articles/duplicate_article/", DuplicationView.as_view(), name="duplicate-article"),  # POST - Dupliquer article
    
    # =============================================================================
    # ITEMS - Gestion des instances d'articles (DataTable)
    # =============================================================================
    
    # Listes d'items (DataTable + filtres avancés + colonnes composées)
    path("items/all_items/", ItemListAPIView.as_view(), name="item-list"),  # GET - Liste items actifs (DataTable)
    path("items/archive/", ArchiveItemListAPIView.as_view(), name="archive-item-list"),  # GET - Liste items archivés (DataTable + Excel)
    path("items/archive/import-excel/", ArchiveItemExcelImportAPIView.as_view(), name="archive-item-import-excel"),  # POST - Import Excel pour archiver des items
    path("items/item_detail/", ItemDetailsAPI.as_view(), name="item-details"),  # GET - Détails d'un item
    
    # CRUD Items
    path("items/get_item/<int:item_id>/", EditItemAPIView.as_view(), name="get-item"),  # GET - Détails item pour édition
    path("items/update_item/<int:item_id>/", ItemUpdateAPIView.as_view(), name="item-update"),  # PUT - Mettre à jour item
    path("items/archive-item/", ArchiverItemAPIView.as_view(), name="archive-item"),  # POST - Archiver/Désarchiver un item
    path("items/archive/batch/", ArchiveItemBatchAPIView.as_view(), name="archive-item-batch"),  # POST - Archiver/Désarchiver plusieurs items
    
    # Opérations et maintenance
    path("items/all_operation/<int:item_id>/", OperationItemListAPIView.as_view(), name="operation-list"),  # GET - Liste opérations d'un item
    path("item/add-operation-item/", AddOperationItemView.as_view(), name="add-operation-item"),  # POST - Ajouter opération
    path("list/operation", operationsListAPIView.as_view(), name="list-operation"),  # GET - Liste toutes opérations
    
    # Affectation et transferts
    path("Affectation/", DuplicationView.as_view(), name="Affectation"),  # POST - Affecter item
    path('items/annuler-affectation/<int:item_id>/', AnnulerAffectationAPIView.as_view(), name='annuler-affectation'),  # POST - Annuler affectation
    path("transfert/", UpdateArticleEmplacement.as_view(), name="transfert"),  # POST - Transférer item
    path('transfers/<int:item_transfer>/', TransferHistoriqueListView.as_view(), name='transfer-historique-list'),  # GET - Historique transferts (DataTable)
    
    # =============================================================================
    # INVENTAIRES - Gestion par niveau hiérarchique (DataTable)
    # =============================================================================
    
    # Inventaires par EMPLACEMENT
    path("inventaire/all_inventaire/", InventaireEmplacementListAPIView.as_view(), name="inventaires-list"),  # GET - Liste inventaires emplacement (DataTable)
    path("inventaire/create_inventaire_emplacement/", InventaireEmplacementCreateAPIView.as_view(), name="inventaire-create"),  # POST - Créer inventaire emplacement
    path("inventaire/edit_inventaire/<int:inventaire_id>/", InventaireEmplacementDetailAPIView.as_view(), name="edit_inventaire"),  # GET - Détails emplacements d'inventaire (DataTable)
    path("inventaire/update_inventaire/<int:inventaire_id>/", InventaireEmplacementUpdateAPIView.as_view(), name="inventaire-update"),  # PUT - Mettre à jour inventaire
    path("inventaire/inventaire_detail_emplacement/<int:inventaire_id>/", InventaireEmplacementsDetailAPIView.as_view(), name="details_inventaire"),  # GET - Détails avec opérateurs (DataTable)
    
    # Inventaires par ZONE
    path("inventaire/all_inventaire_zone/", InventaireZoneListsAPIView.as_view(), name="inventaires-zone-list"),  # GET - Liste inventaires zone (DataTable)
    path("inventaire/create_inventaire_zone/", InventaireZoneCreateAPIView.as_view(), name="inventaire-zone-create"),  # POST - Créer inventaire zone
    path("inventaire/edit_inventaire_zone/<int:inventaire_id>/", InventaireZoneDetailsAPIView.as_view(), name="edit_inventaire_zone"),  # GET - Éditer inventaire zone
    path("inventaire/update_inventaire_zone/<int:inventaire_id>/", InventaireZoneUpdatesAPIView.as_view(), name="inventaire-zone-update"),  # PUT - Mettre à jour inventaire zone
    
    # Inventaires par LOCATION
    path("inventaire/all_inventaire_location/", InventaireLocationListsAPIView.as_view(), name="inventaires-location-list"),  # GET - Liste inventaires location (DataTable)
    path("inventaire/create_inventaire_location/", InventaireLocationCreateAPIView.as_view(), name="inventaire-location-create"),  # POST - Créer inventaire location
    path("inventaire/edit_inventaire_location/<int:inventaire_id>/", InventaireLocationDetailAPIView.as_view(), name="edit_inventaire_location"),  # GET - Éditer inventaire location
    path("inventaire/update_inventaire_location/<int:inventaire_id>/", InventaireLocationUpdateAPIView.as_view(), name="inventaire-location-update"),  # PUT - Mettre à jour inventaire location
    
    # Inventaires par DÉPARTEMENT
    path("inventaire/all_inventaire_departement/", InventaireDepartementListAPIView.as_view(), name="inventaires-departement-list"),  # GET - Liste inventaires département (DataTable)
    path("inventaire/create_inventaire_departement/", InventaireCreateByDepartementAPIView.as_view(), name="inventaire-departement-create"),  # POST - Créer inventaire département
    path("inventaire/edit_inventaire_departement/<int:inventaire_id>/", InventaireDepartementDetailAPIView.as_view(), name="edit_inventaire_departement"),  # GET - Éditer inventaire département
    path("inventaire/update_inventaire_departement/<int:inventaire_id>/", InventaireDepartementUpdateAPIView.as_view(), name="inventaire-departement-update"),  # PUT - Mettre à jour inventaire département
    
    # Opérations sur inventaires
    path('inventaire/info/<int:inventaire_id>/', InfoInventaire.as_view(), name='info-inventaire'),  # GET - Info inventaire
    path("inventaire/lancer_inventaire/", ModifierStatutInventaireEmplacement.as_view(), name="lancer-inventaire"),  # POST - Lancer inventaire
    path("inventaire/update-start-at/", UpdateStartAtAPIView.as_view(), name="update-start-at"),  # PUT - Démarrer inventaire
    path("inventaire/emplacements-count/<int:inventaire_id>/", InventaireEmplacementCountAPIView.as_view(), name="inventaire-emplacement-count"),  # GET - Count emplacements
    
    # Détails d'inventaire
    path("inventaire/create-detail-inventaire/", CreateDetailInventaireView.as_view(), name="create-detail-inventaire"),  # POST - Créer ligne d'inventaire
    path("inventaire/detail-inventaire/<int:inventaire_id>/", DetailInventaireListAPIView.as_view(), name="detail-inventaire-list"),  # GET - Liste détails inventaire (DataTable + Excel)
    
    # Vérifications inventaire
    path("inventaire/", VerifyTagsLocationAPI.as_view(), name="inventaire-verify"),  # POST - Vérifier tags location
    path("inventaire_non_planifier/", VerifyTagsNonPlanifierAPI.as_view(), name="inventaire-non-planifier"),  # POST - Inventaire non planifié
    
    # =============================================================================
    # KPIs ET DASHBOARD - Statistiques et indicateurs de performance
    # =============================================================================
    
    # Dashboard principal - Tous les KPIs en une requête
    path("kpi/dashboard/", KPIDashboardAPIView.as_view(), name="kpi-dashboard"),  # GET - Dashboard principal avec tous les KPIs
    
    
    # =============================================================================
    # ENDPOINTS INDIVIDUELS POUR CHAQUE KPI
    # =============================================================================
    
    # KPIs basés sur la quantité
    path("kpi/total-articles/", TotalArticlesAPIView.as_view(), name="kpi-total-articles"),  # GET - Total articles
    path("kpi/articles-par-fournisseur/", ArticlesParFournisseurAPIView.as_view(), name="kpi-articles-fournisseur"),  # GET - Articles par fournisseur
    path("kpi/articles-par-famille/", ArticlesParFamilleAPIView.as_view(), name="kpi-articles-famille"),  # GET - Articles par famille
    path("kpi/articles-par-categorie/", ArticlesParCategorieAPIView.as_view(), name="kpi-articles-categorie"),  # GET - Articles par catégorie
    path("kpi/articles-par-nature/", ArticlesParNatureAPIView.as_view(), name="kpi-articles-nature"),  # GET - Articles par nature
    path("kpi/total-transferts/", TotalTransfertsAPIView.as_view(), name="kpi-total-transferts"),  # GET - Total transferts
    
    # KPIs basés sur la valeur
    path("kpi/valeur-totale-achats/", ValeurTotaleAchatsAPIView.as_view(), name="kpi-valeur-totale-achats"),  # GET - Valeur totale des achats
    path("kpi/valeur-par-fournisseur/", ValeurParFournisseurAPIView.as_view(), name="kpi-valeur-fournisseur"),  # GET - Valeur par fournisseur
    
    # KPIs de performance
    path("kpi/taux-affectation/", TauxAffectationAPIView.as_view(), name="kpi-taux-affectation"),  # GET - Taux d'affectation
    path("kpi/valeur-residuelle-totale/", ValeurResiduelleTotaleAPIView.as_view(), name="kpi-valeur-residuelle"),  # GET - Valeur résiduelle totale
    path("kpi/items-par-departement/", ItemsParDepartementAPIView.as_view(), name="kpi-items-departement"),  # GET - Items par département
    path("kpi/total-items/", TotalItemsAPIView.as_view(), name="kpi-total-items"),  # GET - Total items
    path("kpi/items-archives/", ItemsArchivesAPIView.as_view(), name="kpi-items-archives"),  # GET - Items archivés
    path("kpi/total-emplacements/", TotalEmplacementsAPIView.as_view(), name="kpi-total-emplacements"),  # GET - Total emplacements
    path("kpi/total-locations/", TotalLocationsAPIView.as_view(), name="kpi-total-locations"),  # GET - Total locations
    path("kpi/total-zones/", TotalZonesAPIView.as_view(), name="kpi-total-zones"),  # GET - Total zones
    path("kpi/tags-affectation/", TagsAffectationAPIView.as_view(), name="kpi-tags-affectation"),  # GET - Tags affectés et non affectés
    
    # Compteurs de base (KPIs principaux) - APIs existantes
    path("article/count/", ArticleCountView.as_view(), name="article-count"),  # GET - Nombre d'articles (qte = qte_recue)
    path("items/count/", ItemsCountCountView.as_view(), name="item-count"),  # GET - Nombre d'items actifs
    path("items/archive/count/", ArchivedItemsCountView.as_view(), name="item-archive-count"),  # GET - Nombre d'items archivés
    path("tags/count/", TagsCountCountView.as_view(), name="tag-count"),  # GET - Nombre de tags non affectés
    
    # Distribution par catégorie
    path("categories/items-count/", CategorieItemCountView.as_view(), name="categories-items-count"),  # GET - Items par catégorie
    path("type_tags/tags-count/", TypeTagCountCountView.as_view(), name="type-tags-tags-count"),  # GET - Tags par type
    path('locations-count/', LocationListAPIView.as_view(), name='location-count'),  # GET - Emplacements par location
    path('departements-item-count/', DepartementListView.as_view(), name='departement-count'),  # GET - Items par département
    
    # Analyses financières et amortissement
    path('valeur-residuelle-global/', GlobalResidualValueAPIView.as_view(), name='valeur-residuelle-global'),  # GET - Valeur résiduelle globale
    path('valeur-residuelle-par-categorie/', ResidualValueByCategoryAPIView.as_view(), name='valeur-residuelle-par-categorie'),  # GET - Valeur résiduelle par catégorie
    path("residual-value/global/current-year/", ResidualValueGlobalCurrentYearView.as_view(), name='residual-value-global-current-year'),  # GET - Valeur résiduelle année courante
    path('financial-value-by-department/<int:year>/', FinancialValueByDepartmentView.as_view(), name='financial-value-by-department'),  # GET - Valeur financière par département/année
    path("item/amortization-count/<int:year>/", AmortizationCountView.as_view(), name="amortization-count"),  # GET - Items amortis/non amortis par année
    
    # Analyses par personne
    path('items/personnes/summaries/', PersonneItemSummaryListView.as_view(), name='personne-item-summaries'),  # GET - Items et valeur par personne
    
    # =============================================================================
    # CONFIGURATION ET ADMINISTRATION
    # =============================================================================
    
    # Internationalisation
    path("set_language/", set_language, name="set_language"),  # POST - Changer langue
    

]

# =============================================================================
# CONFIGURATION DES FICHIERS STATIQUES (Development only)
# =============================================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
═══════════════════════════════════════════════════════════════════════════════
DOCUMENTATION DES ENDPOINTS AMS (Asset Management System)
═══════════════════════════════════════════════════════════════════════════════

📊 12 APIs AVEC SUPPORT DATATABLE (Server-Side Processing)
═══════════════════════════════════════════════════════════════════════════════

1. ArticlesListAPIView                    - Liste articles avec export Excel
2. ItemListAPIView                        - Liste items actifs avec colonnes composées
3. ArchiveItemListAPIView                 - Liste items archivés avec export Excel
4. InventaireEmplacementListAPIView       - Liste inventaires par emplacement
5. InventaireLocationListsAPIView         - Liste inventaires par location
6. InventaireZoneListsAPIView             - Liste inventaires par zone
7. InventaireDepartementListAPIView       - Liste inventaires par département
8. InventaireEmplacementDetailAPIView     - Détails emplacements d'inventaire
9. InventaireEmplacementsDetailAPIView    - Détails avec opérateurs affectés
10. ArticlesConsommesListAPIView          - Articles avec qte_recue = 0
11. TransferHistoriqueListView            - Historique des transferts d'item
12. DetailInventaireListAPIView           - Détails d'inventaire avec export Excel

═══════════════════════════════════════════════════════════════════════════════
EXEMPLES D'UTILISATION DATATABLE
═══════════════════════════════════════════════════════════════════════════════

📌 PAGINATION BASIQUE:
GET /items/all_items/?draw=1&start=0&length=20

📌 RECHERCHE GLOBALE:
GET /items/all_items/?search[value]=Bureau

📌 TRI PAR COLONNE:
GET /items/all_items/?ordering=-created_at
GET /items/all_items/?ordering=article__designation

📌 FILTRE SIMPLE (exact match):
GET /items/all_items/?statut_exact=affecter
GET /items/all_items/?departement_exact=IT

📌 FILTRE PARTIEL (contains):
GET /items/all_items/?emplacement_icontains=salle

📌 FILTRE SUR COLONNE COMPOSÉE (nom complet):
GET /items/all_items/?affectation_personne_full_name_icontains=ASSOULI+khadija
GET /items/all_items/?article_full_name_icontains=Dell+Latitude

📌 FILTRES MULTIPLES:
GET /items/all_items/?statut_exact=affecter&departement_exact=IT&zone_icontains=Zone+A

📌 TRI + FILTRE + PAGINATION:
GET /items/all_items/?draw=1&start=0&length=20&ordering=-created_at&statut_exact=affecter

📌 EXPORT EXCEL:
GET /items/archive/?export=excel
GET /inventaire/detail-inventaire/1/?export=excel

═══════════════════════════════════════════════════════════════════════════════
OPÉRATEURS DE FILTRE SUPPORTÉS
═══════════════════════════════════════════════════════════════════════════════

Chaînes de caractères:
  _exact        → Correspondance exacte (case-insensitive)
  _icontains    → Contient (case-insensitive)
  _istartswith  → Commence par (case-insensitive)
  _iendswith    → Se termine par (case-insensitive)

Nombres:
  _exact        → Égal à
  _gt           → Plus grand que
  _gte          → Plus grand ou égal à
  _lt           → Plus petit que
  _lte          → Plus petit ou égal à
  _range        → Entre deux valeurs

Dates:
  _exact        → Date exacte
  _gte          → Après ou égal à
  _lte          → Avant ou égal à
  _year         → Année spécifique
  _month        → Mois spécifique
  _range        → Entre deux dates

═══════════════════════════════════════════════════════════════════════════════
COLONNES COMPOSÉES (Composite Columns)
═══════════════════════════════════════════════════════════════════════════════

Certaines colonnes combinent plusieurs champs:

affectation_personne_full_name  → nom + " " + prenom
article_full_name               → designation + " - " + code_article

Exemples:
  ?affectation_personne_full_name_exact=ASSOULI khadija
  ?affectation_personne_full_name_icontains=khadija
  ?article_full_name_icontains=Dell

═══════════════════════════════════════════════════════════════════════════════
RÉPONSE DATATABLE (Format Standard)
═══════════════════════════════════════════════════════════════════════════════

{
  "draw": 1,
  "recordsTotal": 150,        // Total sans filtre
  "recordsFiltered": 23,      // Total avec filtres appliqués
  "data": [...]               // Tableau des résultats
}

📌 recordsTotal    : Nombre total d'enregistrements dans la base
📌 recordsFiltered : Nombre d'enregistrements après application des filtres
📌 data            : Résultats de la page actuelle

═══════════════════════════════════════════════════════════════════════════════
AUTHENTIFICATION
═══════════════════════════════════════════════════════════════════════════════

POST /login/mobile/              → Login mobile
POST /api/token/                 → Obtenir token JWT
POST /api/token/refresh/         → Rafraîchir token
POST /api/token/verify/          → Vérifier token
GET  /user/permissions/          → Permissions utilisateur

═══════════════════════════════════════════════════════════════════════════════
KPIs PRINCIPAUX
═══════════════════════════════════════════════════════════════════════════════

Compteurs:
  /article/count/                    → Nombre d'articles (qte = qte_recue)
  /items/count/                      → Nombre d'items actifs
  /items/archive/count/              → Nombre d'items archivés
  /tags/count/                       → Nombre de tags disponibles

Distribution:
  /categories/items-count/           → Items par catégorie
  /departements-item-count/          → Items par département
  /locations-count/                  → Emplacements par location

Analyses financières:
  /valeur-residuelle-global/         → Valeur résiduelle totale
  /valeur-residuelle-par-categorie/  → Valeur résiduelle par catégorie
  /financial-value-by-department/<year>/ → Valeur par département
  /item/amortization-count/<year>/   → Items amortis vs non amortis

═══════════════════════════════════════════════════════════════════════════════
MOBILE API
═══════════════════════════════════════════════════════════════════════════════

Endpoints optimisés pour mobile avec /mobile/ prefix:
- Réponses allégées
- Support pagination simplifiée
- Données essentielles uniquement

GET /mobile/all_location/          → Locations
GET /mobile/zones/                 → Zones
GET /mobile/emplacements/          → Emplacements
GET /mobile/article/all_articles/  → Articles
GET /mobiel/inventaire/all_inventaire/ → Inventaires

═══════════════════════════════════════════════════════════════════════════════
"""