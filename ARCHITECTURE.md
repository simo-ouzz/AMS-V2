# Architecture AMS (Asset Management System)

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture actuelle](#architecture-actuelle)
3. [Architecture recommandée](#architecture-recommandée)
4. [Structure des dossiers](#structure-des-dossiers)
5. [Patterns et bonnes pratiques](#patterns-et-bonnes-pratiques)
6. [Plan de migration](#plan-de-migration)
7. [Standards de code](#standards-de-code)

---

## 📐 Vue d'ensemble

### Technologies utilisées

**Backend :**
- Django 4.x
- Django REST Framework
- PostgreSQL
- JWT Authentication
- Django Filters
- Openpyxl (export)

**Frontend :**
- Vue 3 + TypeScript
- Composition API
- DataTable.js
- Axios

---

## 🏗️ Architecture actuelle

### Structure actuelle

```
backend/
├── masterdata/              # ⚠️ Monolithique - Tout dans une seule app
│   ├── models.py           # ❌ 4000+ lignes
│   ├── views.py            # ❌ 4500+ lignes
│   ├── serializers.py      # ❌ 1000+ lignes
│   ├── urls.py             # ✅ 650 lignes (documenté)
│   └── config/             # ⚠️ Filtres séparés (bon début)
├── datatables/             # ✅ Package bien structuré
├── project/                # ✅ Configuration Django
└── static/                 # ⚠️ Assets frontend + backend mélangés
```

### Problèmes identifiés

❌ **Monolithe** : Tout dans `masterdata/`  
❌ **Fichiers géants** : `views.py` (4500 lignes), `models.py` (4000 lignes)  
❌ **Responsabilités mélangées** : Business logic dans les views  
❌ **Tests manquants** : Pas de structure de tests  
❌ **Duplication** : Code répété entre views similaires  
❌ **Couplage fort** : Dépendances circulaires  

---

## 🎯 Architecture recommandée

### Principes directeurs

1. **Domain-Driven Design (DDD)** - Organisation par domaine métier
2. **SOLID** - Déjà appliqué dans `datatables/`, à étendre
3. **Clean Architecture** - Séparation des couches
4. **API First** - Backend comme service REST pur
5. **Testabilité** - Code facilement testable

### Schéma de l'architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Vue 3)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Views → Composables → Services → API Client        │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                   API LAYER (DRF)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  URLs → Views → Serializers                          │  │
│  └──────────────────────┬───────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│               BUSINESS LAYER (Services)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Services → Managers → Business Logic                │  │
│  └──────────────────────┬───────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│                DATA LAYER (Models + ORM)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Models → Repositories → QuerySets                   │  │
│  └──────────────────────┬───────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│                  DATABASE (PostgreSQL)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Structure des dossiers recommandée

### Option 1 : Organisation par domaine métier (DDD) ⭐ RECOMMANDÉ

```
backend/
├── apps/                           # Applications Django par domaine
│   │
│   ├── core/                       # Fonctionnalités partagées
│   │   ├── __init__.py
│   │   ├── models.py              # Modèles abstraits de base
│   │   ├── managers.py            # Managers personnalisés
│   │   ├── mixins.py              # Mixins réutilisables
│   │   ├── permissions.py         # Permissions personnalisées
│   │   ├── validators.py          # Validateurs
│   │   ├── utils.py               # Utilitaires
│   │   └── exceptions.py          # Exceptions personnalisées
│   │
│   ├── authentication/            # 🔐 Authentification et utilisateurs
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── compte.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   └── user_service.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   └── urls.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_models.py
│   │   │   ├── test_services.py
│   │   │   └── test_api.py
│   │   └── apps.py
│   │
│   ├── catalog/                   # 📦 Catalogue (Articles, Produits)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── article.py        # Article model
│   │   │   ├── produit.py        # Produit model
│   │   │   ├── categorie.py      # Categorie model
│   │   │   ├── famille.py        # Famille model
│   │   │   ├── marque.py         # Marque model
│   │   │   └── fournisseur.py    # Fournisseur model
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── article_service.py
│   │   │   ├── import_service.py
│   │   │   └── export_service.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── article_views.py
│   │   │   │   └── produit_views.py
│   │   │   ├── serializers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── article_serializers.py
│   │   │   │   └── produit_serializers.py
│   │   │   ├── filters/
│   │   │   │   ├── __init__.py
│   │   │   │   └── article_filters.py
│   │   │   └── urls.py
│   │   ├── repositories/          # Pattern Repository (optionnel)
│   │   │   ├── __init__.py
│   │   │   └── article_repository.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_models.py
│   │   │   ├── test_services.py
│   │   │   └── test_api.py
│   │   └── apps.py
│   │
│   ├── assets/                    # 🏷️ Gestion des actifs (Items)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── item.py
│   │   │   ├── tag.py
│   │   │   ├── operation.py
│   │   │   └── historique.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── item_service.py
│   │   │   ├── affectation_service.py
│   │   │   ├── transfer_service.py
│   │   │   ├── amortization_service.py
│   │   │   └── archive_service.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── item_views.py
│   │   │   │   ├── tag_views.py
│   │   │   │   └── operation_views.py
│   │   │   ├── serializers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── item_serializers.py
│   │   │   │   └── tag_serializers.py
│   │   │   ├── filters/
│   │   │   │   ├── __init__.py
│   │   │   │   └── item_filters.py
│   │   │   └── urls.py
│   │   ├── tasks/                 # Tâches Celery (optionnel)
│   │   │   ├── __init__.py
│   │   │   └── amortization_tasks.py
│   │   ├── tests/
│   │   └── apps.py
│   │
│   ├── organization/              # 🏢 Organisation (Dép., Emp., Zones)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── departement.py
│   │   │   ├── emplacement.py
│   │   │   ├── zone.py
│   │   │   ├── location.py
│   │   │   └── personne.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── organization_service.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   └── urls.py
│   │   ├── tests/
│   │   └── apps.py
│   │
│   ├── inventory/                 # 📋 Inventaires
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── inventaire.py
│   │   │   ├── inventaire_emplacement.py
│   │   │   └── detail_inventaire.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── inventaire_service.py
│   │   │   ├── verification_service.py
│   │   │   └── rfid_service.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── inventaire_views.py
│   │   │   │   ├── zone_views.py
│   │   │   │   ├── location_views.py
│   │   │   │   └── departement_views.py
│   │   │   ├── serializers/
│   │   │   │   ├── __init__.py
│   │   │   │   └── inventaire_serializers.py
│   │   │   ├── filters/
│   │   │   │   ├── __init__.py
│   │   │   │   └── inventaire_filters.py
│   │   │   └── urls.py
│   │   ├── tests/
│   │   └── apps.py
│   │
│   ├── analytics/                 # 📊 KPIs et Dashboard
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── kpi_service.py
│   │   │   ├── financial_service.py
│   │   │   └── statistics_service.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dashboard_views.py
│   │   │   │   └── kpi_views.py
│   │   │   ├── serializers/
│   │   │   │   ├── __init__.py
│   │   │   │   └── kpi_serializers.py
│   │   │   └── urls.py
│   │   ├── tests/
│   │   └── apps.py
│   │
│   └── mobile/                    # 📱 API Mobile spécifique
│       ├── api/
│       │   ├── __init__.py
│       │   ├── views.py
│       │   ├── serializers.py
│       │   └── urls.py
│       ├── tests/
│       └── apps.py
│
├── datatables/                    # ✅ Package DataTable (déjà bien fait)
│   ├── __init__.py
│   ├── base.py
│   ├── mixins.py
│   ├── filters.py
│   ├── serializers.py
│   ├── exporters.py
│   └── docs/
│
├── config/                        # Configuration Django
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py               # Settings de base
│   │   ├── development.py        # Settings dev
│   │   ├── production.py         # Settings prod
│   │   └── test.py               # Settings tests
│   ├── urls.py                   # URLs racine
│   ├── wsgi.py
│   └── asgi.py
│
├── tests/                         # Tests d'intégration
│   ├── __init__.py
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│
├── docs/                          # Documentation
│   ├── api/
│   ├── architecture/
│   └── deployment/
│
├── scripts/                       # Scripts utilitaires
│   ├── setup_dev.sh
│   ├── seed_data.py
│   └── backup_db.sh
│
├── requirements/                  # Requirements séparés
│   ├── base.txt
│   ├── development.txt
│   ├── production.txt
│   └── test.txt
│
├── manage.py
├── pytest.ini
├── .env.example
├── .gitignore
├── README.md
└── ARCHITECTURE.md
```

---

## 🎨 Patterns et bonnes pratiques

### 1. **Service Layer Pattern** ⭐

Séparer la logique métier des views.

**Avant (dans views.py) :**
```python
class ItemListAPIView(ServerSideDataTableView):
    def get_datatable_queryset(self):
        if not self.request.user.compte:
            return item.objects.none()
        
        # ❌ Logique métier dans la vue
        return item.objects.filter(
            article__compte=self.request.user.compte,
            archive=False
        ).select_related(...)
```

**Après (avec Service Layer) :**

```python
# apps/assets/services/item_service.py
class ItemService:
    """Service pour la gestion des items"""
    
    @staticmethod
    def get_active_items(compte):
        """Retourne les items actifs pour un compte"""
        if not compte:
            return item.objects.none()
        
        return item.objects.filter(
            article__compte=compte,
            archive=False
        ).select_related(
            'article',
            'article__produit',
            'emplacement',
            'departement',
            'affectation_personne'
        )
    
    @staticmethod
    def calculate_residual_value(item_obj):
        """Calcule la valeur résiduelle d'un item"""
        if not item_obj.article:
            return None
        
        # ... logique de calcul
        return valeur_residuelle
    
    @staticmethod
    def assign_to_person(item_obj, personne, user):
        """Affecte un item à une personne"""
        # Validation
        if item_obj.statut not in ['stock', 'disponible']:
            raise ValidationError("Item non disponible")
        
        # Business logic
        item_obj.affectation_personne = personne
        item_obj.statut = 'affecter'
        item_obj.date_affectation = timezone.now()
        item_obj.save()
        
        # Historique
        HistoriqueItem.objects.create(
            item=item_obj,
            action='affectation',
            user=user,
            details=f"Affecté à {personne.nom} {personne.prenom}"
        )
        
        return item_obj

# apps/assets/api/views/item_views.py
class ItemListAPIView(ServerSideDataTableView):
    model = item
    serializer_class = ItemsSerializer
    
    # ✅ Vue simple, logique dans le service
    def get_datatable_queryset(self):
        return ItemService.get_active_items(self.request.user.compte)
```

### 2. **Repository Pattern** (optionnel mais recommandé)

Encapsuler l'accès aux données.

```python
# apps/assets/repositories/item_repository.py
class ItemRepository:
    """Repository pour l'accès aux données Item"""
    
    @staticmethod
    def get_by_reference(reference: str, compte) -> Optional[Item]:
        """Récupère un item par sa référence"""
        try:
            return Item.objects.select_related(
                'article', 'emplacement', 'departement'
            ).get(
                reference_auto=reference,
                article__compte=compte
            )
        except Item.DoesNotExist:
            return None
    
    @staticmethod
    def get_active_items(compte, filters: dict = None) -> QuerySet:
        """Retourne les items actifs avec filtres optionnels"""
        queryset = Item.objects.filter(
            article__compte=compte,
            archive=False
        ).select_related('article', 'emplacement')
        
        if filters:
            if 'statut' in filters:
                queryset = queryset.filter(statut=filters['statut'])
            if 'departement' in filters:
                queryset = queryset.filter(departement_id=filters['departement'])
        
        return queryset
    
    @staticmethod
    def count_by_status(compte) -> dict:
        """Compte les items par statut"""
        return Item.objects.filter(
            article__compte=compte,
            archive=False
        ).values('statut').annotate(count=Count('id'))

# Utilisation dans le service
class ItemService:
    def __init__(self):
        self.repository = ItemRepository()
    
    def get_item_by_reference(self, reference, compte):
        item = self.repository.get_by_reference(reference, compte)
        if not item:
            raise ItemNotFoundError(f"Item {reference} non trouvé")
        return item
```

### 3. **Manager personnalisé**

Pour les requêtes complexes fréquentes.

```python
# apps/assets/models/item.py
class ItemQuerySet(models.QuerySet):
    """QuerySet personnalisé pour Item"""
    
    def active(self):
        """Items non archivés"""
        return self.filter(archive=False)
    
    def by_compte(self, compte):
        """Items d'un compte"""
        return self.filter(article__compte=compte)
    
    def with_relations(self):
        """Items avec relations préchargées"""
        return self.select_related(
            'article',
            'article__produit',
            'emplacement',
            'departement',
            'affectation_personne'
        )
    
    def assigned(self):
        """Items affectés"""
        return self.filter(statut='affecter', affectation_personne__isnull=False)
    
    def in_stock(self):
        """Items en stock"""
        return self.filter(statut='stock')
    
    def by_department(self, departement):
        """Items d'un département"""
        return self.filter(departement=departement)

class ItemManager(models.Manager):
    """Manager personnalisé pour Item"""
    
    def get_queryset(self):
        return ItemQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def by_compte(self, compte):
        return self.get_queryset().by_compte(compte)
    
    def with_relations(self):
        return self.get_queryset().with_relations()

class Item(models.Model):
    # ... fields ...
    
    objects = ItemManager()  # ✅ Manager personnalisé
    
    class Meta:
        db_table = 'item'
        ordering = ['-created_at']

# Utilisation
items = Item.objects.active().by_compte(compte).with_relations()
assigned_items = Item.objects.active().assigned().by_department(dept)
```

### 4. **Serializers hiérarchiques**

Organiser les serializers par complexité.

```python
# apps/assets/api/serializers/item_serializers.py

# Serializer de base (minimal)
class ItemMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les listes"""
    class Meta:
        model = Item
        fields = ['id', 'reference_auto', 'statut']

# Serializer standard
class ItemSerializer(serializers.ModelSerializer):
    """Serializer standard avec relations"""
    article_designation = serializers.CharField(source='article.designation', read_only=True)
    emplacement_nom = serializers.CharField(source='emplacement.nom', read_only=True)
    
    class Meta:
        model = Item
        fields = [
            'id', 'reference_auto', 'numero_serie',
            'article_designation', 'emplacement_nom',
            'statut', 'created_at'
        ]

# Serializer détaillé
class ItemDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les vues de détail"""
    article = ArticleSerializer(read_only=True)
    emplacement = EmplacementSerializer(read_only=True)
    departement = DepartementSerializer(read_only=True)
    affectation_personne = PersonneSerializer(read_only=True)
    valeur_residuelle = serializers.SerializerMethodField()
    historique = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = '__all__'
    
    def get_valeur_residuelle(self, obj):
        return ItemService.calculate_residual_value(obj)
    
    def get_historique(self, obj):
        historique = obj.historique_set.all()[:5]
        return HistoriqueSerializer(historique, many=True).data

# Serializer pour création/modification
class ItemWriteSerializer(serializers.ModelSerializer):
    """Serializer pour CREATE/UPDATE"""
    class Meta:
        model = Item
        fields = [
            'reference_auto', 'numero_serie',
            'article', 'emplacement', 'departement',
            'affectation_personne', 'statut'
        ]
    
    def validate(self, data):
        # Validations métier
        if data.get('statut') == 'affecter' and not data.get('affectation_personne'):
            raise serializers.ValidationError(
                "Une personne doit être affectée pour le statut 'affecter'"
            )
        return data
```

### 5. **Views organisées par responsabilité**

```python
# apps/assets/api/views/item_views.py

class ItemListAPIView(ServerSideDataTableView):
    """Liste des items avec DataTable"""
    model = Item
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]
    
    enable_export = True
    export_formats = ['excel', 'csv']
    export_filename = 'items'
    
    search_fields = ['reference_auto', 'numero_serie', 'article__designation']
    ordering_fields = ['id', 'reference_auto', 'created_at']
    
    def get_datatable_queryset(self):
        return ItemService.get_active_items(self.request.user.compte)

class ItemDetailAPIView(generics.RetrieveAPIView):
    """Détails d'un item"""
    serializer_class = ItemDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Item.objects.by_compte(self.request.user.compte).with_relations()

class ItemCreateAPIView(generics.CreateAPIView):
    """Création d'un item"""
    serializer_class = ItemWriteSerializer
    permission_classes = [IsAuthenticated, CanCreateItem]
    
    def perform_create(self, serializer):
        # Logique métier via le service
        item = serializer.save()
        ItemService.initialize_item(item, self.request.user)

class ItemUpdateAPIView(generics.UpdateAPIView):
    """Mise à jour d'un item"""
    serializer_class = ItemWriteSerializer
    permission_classes = [IsAuthenticated, CanUpdateItem]
    
    def get_queryset(self):
        return Item.objects.by_compte(self.request.user.compte)

class ItemAssignAPIView(APIView):
    """Affectation d'un item à une personne"""
    permission_classes = [IsAuthenticated, CanAssignItem]
    
    def post(self, request, item_id):
        item = get_object_or_404(
            Item.objects.by_compte(request.user.compte),
            id=item_id
        )
        personne_id = request.data.get('personne_id')
        personne = get_object_or_404(Personne, id=personne_id)
        
        # ✅ Logique métier dans le service
        try:
            item = ItemService.assign_to_person(item, personne, request.user)
            serializer = ItemSerializer(item)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

### 6. **Tests structurés**

```python
# apps/assets/tests/test_services.py
import pytest
from apps.assets.services import ItemService
from apps.assets.tests.factories import ItemFactory, PersonneFactory

@pytest.mark.django_db
class TestItemService:
    """Tests du service Item"""
    
    def test_get_active_items_returns_only_non_archived(self, compte):
        # Arrange
        ItemFactory.create_batch(3, archive=False, article__compte=compte)
        ItemFactory.create_batch(2, archive=True, article__compte=compte)
        
        # Act
        items = ItemService.get_active_items(compte)
        
        # Assert
        assert items.count() == 3
    
    def test_assign_to_person_updates_status(self, item, personne, user):
        # Arrange
        item.statut = 'stock'
        item.save()
        
        # Act
        result = ItemService.assign_to_person(item, personne, user)
        
        # Assert
        assert result.statut == 'affecter'
        assert result.affectation_personne == personne
        assert result.date_affectation is not None
    
    def test_assign_to_person_raises_error_if_already_assigned(self, item, personne, user):
        # Arrange
        item.statut = 'affecter'
        item.save()
        
        # Act & Assert
        with pytest.raises(ValidationError):
            ItemService.assign_to_person(item, personne, user)

# apps/assets/tests/test_api.py
import pytest
from rest_framework.test import APIClient
from rest_framework import status

@pytest.mark.django_db
class TestItemAPI:
    """Tests de l'API Item"""
    
    def test_list_items_returns_200(self, api_client, authenticated_user, items):
        # Act
        response = api_client.get('/items/all_items/')
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.json()
    
    def test_export_excel_returns_file(self, api_client, authenticated_user, items):
        # Act
        response = api_client.get('/items/all_items/?export=excel')
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
```

### 7. **Configuration par environnement**

```python
# config/settings/base.py
"""Settings communs à tous les environnements"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ...
    
    # Apps locales
    'apps.core',
    'apps.authentication',
    'apps.catalog',
    'apps.assets',
    'apps.organization',
    'apps.inventory',
    'apps.analytics',
    'apps.mobile',
    
    # Packages
    'datatables',
    
    # Third-party
    'rest_framework',
    'django_filters',
    'corsheaders',
]

# config/settings/development.py
"""Settings pour développement"""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ams_dev',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# config/settings/production.py
"""Settings pour production"""
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Sécurité
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 🚀 Plan de migration

### Phase 1 : Préparation (1-2 jours)

1. ✅ Créer la nouvelle structure de dossiers
2. ✅ Configurer les settings par environnement
3. ✅ Mettre en place pytest et les factories
4. ✅ Documenter l'architecture

### Phase 2 : Migration progressive (2-3 semaines)

**Semaine 1 : Core et Authentication**
- Créer `apps/core/` avec les classes de base
- Migrer l'authentification vers `apps/authentication/`
- Écrire les tests

**Semaine 2 : Catalog et Assets**
- Migrer les modèles Article, Produit vers `apps/catalog/`
- Migrer Item, Tag vers `apps/assets/`
- Créer les services

**Semaine 3 : Organization et Inventory**
- Migrer Départements, Emplacements vers `apps/organization/`
- Migrer Inventaires vers `apps/inventory/`
- Créer les services

**Semaine 4 : Analytics et Mobile**
- Migrer les KPIs vers `apps/analytics/`
- Séparer les APIs mobile dans `apps/mobile/`
- Tests d'intégration

### Phase 3 : Refactoring (1-2 semaines)

- Extraire la logique métier des views vers les services
- Implémenter les repositories
- Ajouter les managers personnalisés
- Tests unitaires complets

### Phase 4 : Optimisation (ongoing)

- Monitoring et logging
- Cache (Redis)
- Celery pour tâches asynchrones
- Documentation API (Swagger)

---

## 📏 Standards de code

### Conventions de nommage

```python
# ✅ BON
class ItemService:
    def get_active_items(self, compte):
        pass
    
    def calculate_residual_value(self, item):
        pass

# ❌ MAUVAIS
class itemService:
    def getActiveItems(self, compte):  # camelCase
        pass
```

### Structure d'un fichier Python

```python
"""
Module docstring expliquant le but du fichier
"""

# Imports standard library
import os
from datetime import datetime

# Imports Django
from django.db import models
from django.utils import timezone

# Imports third-party
from rest_framework import serializers

# Imports locaux
from apps.core.models import BaseModel
from apps.catalog.models import Article

# Constants
DEFAULT_STATUS = 'stock'
MAX_ITEMS_PER_PAGE = 100

# Classes
class ItemService:
    """Service pour la gestion des items"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def method(self):
        """Docstring de la méthode"""
        pass
```

### Documentation

```python
def calculate_residual_value(item: Item, reference_date: date = None) -> Decimal:
    """
    Calcule la valeur résiduelle d'un item à une date donnée.
    
    Args:
        item: Instance de l'item
        reference_date: Date de référence pour le calcul (défaut: aujourd'hui)
    
    Returns:
        Valeur résiduelle en Decimal
    
    Raises:
        ValueError: Si l'item n'a pas d'article associé
        
    Example:
        >>> item = Item.objects.get(id=1)
        >>> valeur = calculate_residual_value(item)
        >>> print(valeur)
        Decimal('1500.00')
    """
    if not item.article:
        raise ValueError("L'item doit avoir un article associé")
    
    # ... logique
    return valeur_residuelle
```

---

## 📚 Ressources

- **Django Best Practices** : https://django-best-practices.readthedocs.io/
- **Two Scoops of Django** : https://www.feldroy.com/books/two-scoops-of-django-3-x
- **DRF Best Practices** : https://www.django-rest-framework.org/topics/best-practices/
- **Clean Architecture** : https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html

---

**Prochaines étapes recommandées :**

1. ✅ Lire et valider cette architecture
2. ⏭️  Décider : Migration progressive ou réécriture ?
3. ⏭️  Commencer par `apps/core/` et `apps/authentication/`
4. ⏭️  Mettre en place les tests dès le début
5. ⏭️  Migrer module par module

**Questions ? N'hésitez pas à demander des éclaircissements ! 🚀**

