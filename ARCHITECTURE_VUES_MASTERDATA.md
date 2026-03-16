## Architecture fonctionnelle ciblée

**Objectif**: organiser le code backend `masterdata` selon les couches suivantes :

- **View (API)** → **Serializer (optionnel)** → **Service** → **Repository** → **Model**

Cette architecture sépare :

- **View**: gestion HTTP / permissions / validation très basique.
- **Serializer**: validation et (dé)sérialisation des données d’entrée/sortie.
- **Service**: logique métier, orchestration de plusieurs repositories et règles fonctionnelles.
- **Repository**: accès aux données (Django ORM), requêtes complexes, aucune logique métier.
- **Model**: structure de données et règles d’intégrité proches de la base (constraints, méthodes simples).

---

## Organisation des dossiers proposée

Dans l’application `masterdata`, l’organisation cible pourrait être :

- `masterdata/`
  - `models.py` (ou plusieurs fichiers modèles plus tard)
  - `serializers.py` (serializers “généraux” existants)
  - `views.py` (**à découper progressivement**, voir plus bas)
  - `Views/` (KPIs déjà séparés, à faire évoluer vers la même architecture)
  - `services/`
    - `__init__.py`
    - `articles.py`
    - `items.py`
    - `inventaires.py`
    - `tags.py`
    - `operations.py`
  - `repositories/`
    - `__init__.py`
    - `article_repository.py`
    - `item_repository.py`
    - `inventaire_repository.py`
    - `tag_repository.py`
    - `operation_repository.py`
  - `api/`
    - `__init__.py`
    - `articles_views.py`
    - `items_views.py`
    - `inventaires_views.py`
    - `tags_views.py`
    - `operations_views.py`

À terme :

- `project/urls.py` importe toujours `masterdata.urls`.
- `masterdata/urls.py` importe les vues à partir de `masterdata.api.*` au lieu de `masterdata.views`.

---

## Rôle détaillé de chaque couche

### View (API)

- Reçoit `request` (REST Framework).
- Valide les paramètres “simples” (ex: présence de `id`, `page`, etc.).
- Appelle **un service** pour exécuter la logique métier.
- Retourne un `Response(serializer.data)` ou un format JSON standardisé.
- Ne contient **pas** de requêtes ORM directes (sauf cas très simples de listing).

### Serializer (optionnel)

- Valide les payloads JSON complexes.
- Définit la structure de réponse.
- Peut être :
  - un **serializer d’entrée** (input / command),
  - un **serializer de sortie** (output / query),
  - ou un serializer “mixte” (create / update).

### Service

- Contient la logique métier “pure” d’un domaine (articles, items, inventaires, tags…).
- Orchestration de plusieurs repositories.
- Gère les transactions (si nécessaire) et les règles fonctionnelles :
  - ex: “un tag ne peut pas être affecté deux fois”,
  - ex: “un inventaire ne peut pas être lancé deux fois sur le même emplacement”.
- Ne connaît pas HTTP ni `Request`/`Response`.

### Repository

- Fournit des fonctions **orientées métier** mais limitées à l’accès aux données :
  - `get_article_by_id`, `list_items_by_emplacement`, `find_tags_inventaire`, etc.
- Utilise les **models Django** et l’ORM (filter, select_related, annotate...).
- Ne contient pas de logique métier complexe.
- Retourne des objets modèles ou des QuerySet.

### Model

- Définit la structure de données (champs, relations, contraintes DB).
- Regroupe les méthodes métier “proches” des données, courtes :
  - ex: `item.calculate_residual_value()`.
- Ne connaît pas les HTTP views, ni les serializers.

---

## Exemple concret : flux Inventaire Emplacement

### Situation actuelle

Actuellement, toute la logique est directement dans les vues de `views.py`, par exemple :

- `InventaireEmplacementListAPIView`
- `InventaireEmplacementCreateAPIView`
- `VerifyTagsLocationAPI`
- `VerifyTagsNonPlanifierAPI`
- `CreateDetailInventaireView`

Ces classes mélangent :

- lecture/écriture ORM (`item.objects.filter`, `inventaire.objects.create`, etc.),
- règles métier (classification des tags : correcte, intru, manquant, non_affecter, inconnu),
- formatage de la réponse JSON.

### Cible par couche

- **Views API** (`masterdata/api/inventaires_views.py`) :
  - `InventaireEmplacementCreateAPIView`
  - `InventaireEmplacementListAPIView`
  - `InventaireEmplacementDetailAPIView`
  - `VerifyTagsLocationAPI`
  - `VerifyTagsNonPlanifierAPI`
  - `CreateDetailInventaireView`

- **Services** (`masterdata/services/inventaires.py`) :
  - `create_inventaire_emplacement(...)`
  - `update_inventaire_emplacement(...)`
  - `verify_tags_location(...)` (logique de `VerifyTagsLocationAPI.post`)
  - `verify_tags_non_planifier(...)`
  - `create_detail_inventaire(...)`

- **Repositories** :
  - `inventaire_repository.py` :
    - `get_inventaire_by_id(...)`
    - `list_inventaires_by_compte(...)`
    - `create_inventaire_emplacement(...)`
  - `item_repository.py` :
    - `list_items_by_emplacement(...)`
    - `list_archived_items_by_emplacement(...)`
  - `tag_repository.py` :
    - `list_tags_by_references_and_compte(...)`
    - `list_tags_affectes(...)`

---

## Exemple de découpage pour une vue existante

### 1. Vue (API) – `VerifyTagsLocationAPI`

Fichier cible : `masterdata/api/inventaires_views.py`

```python
class VerifyTagsLocationAPI(APIView):
    def post(self, request):
        serializer = VerifyTagsLocationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = verify_tags_location_service(
            user=request.user,
            tags=serializer.validated_data["tags"],
            emplacement_id=serializer.validated_data["emplacement_id"],
            inventaire_id=serializer.validated_data["inventaire_id"],
        )

        output = VerifyTagsLocationOutputSerializer(result)
        return Response(output.data, status=status.HTTP_200_OK)
```

### 2. Serializer d’entrée / sortie

Fichier cible : `masterdata/serializers_inventaires.py` (ou dans `serializers.py` au début) :

```python
class VerifyTagsLocationInputSerializer(serializers.Serializer):
    tags = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )
    emplacement_id = serializers.IntegerField()
    inventaire_id = serializers.IntegerField()


class VerifyTagsLocationOutputSerializer(serializers.Serializer):
    data = serializers.ListField()
    counts = serializers.DictField(
        child=serializers.IntegerField()
    )
```

### 3. Service – `verify_tags_location_service`

Fichier cible : `masterdata/services/inventaires.py` :

```python
def verify_tags_location_service(user, tags, emplacement_id, inventaire_id):
    """
    Contient la logique actuellement dans VerifyTagsLocationAPI.post :
    - vérification des paramètres
    - appels à verifier_tags_affecter, verifier_emplacement_tags,
      verifier_items_archives, verifier_tags_manquants
    - construction de la structure {data: [...], counts: {...}}
    """
    # TODO: déplacer ici toute la logique métier depuis views.py
    ...
```

### 4. Repositories – accès aux données

Exemples :

```python
# masterdata/repositories/tag_repository.py

from masterdata.models import tag


def list_tags_by_references_and_compte(references, compte):
    return tag.objects.filter(reference__in=references, compte=compte)
```

```python
# masterdata/repositories/item_repository.py

from masterdata.models import item


def list_items_by_emplacement(emplacement_id, archive=False):
    return item.objects.filter(emplacement_id=emplacement_id, archive=archive)
```

Ces fonctions seront appelées depuis `services/inventaires.py` au lieu d’être utilisées directement dans les views.

---

## Stratégie de migration progressive depuis `views.py`

Comme `masterdata/views.py` est très volumineux, il est préférable d’avancer **par fonctionnalité** :

1. **Créer les dossiers** `api/`, `services/`, `repositories/` avec `__init__.py`.
2. Choisir un sous-domaine (par exemple **Inventaire Emplacement**).
3. Pour ce sous-domaine :
   - Créer un fichier `api/inventaires_views.py`.
   - Déplacer une première vue (ex: `InventaireEmplacementCreateAPIView`).
   - Extraire la logique métier dans un service `services/inventaires.py`.
   - Extraire les accès base dans `repositories/inventaire_repository.py` et `repositories/item_repository.py`.
   - Ajouter/ajuster les serializers si nécessaire.
4. Mettre à jour `masterdata/urls.py` pour importer la vue depuis `masterdata.api.inventaires_views`.
5. Lancer les tests / vérifier manuellement l’API.
6. Répéter pour les autres groupes :
   - **Articles** → `articles_views.py`, `services/articles.py`, `repositories/article_repository.py`.
   - **Items** → `items_views.py`, `services/items.py`, `repositories/item_repository.py`.
   - **Tags** → `tags_views.py`, `services/tags.py`, `repositories/tag_repository.py`.
   - **Opérations / Historique** → `operations_views.py`, `services/operations.py`, `repositories/operation_repository.py`.

Pendant la transition, il est possible de :

- Laisser certaines vues **temporairement** dans `views.py`.
- Introduire les nouvelles vues dans `api/` en parallèle.
- Garder la compatibilité des routes en ne changeant que les imports dans `urls.py`.

---

## Consignes de style pour les nouvelles views

- **Une vue = une responsabilité** claire (ou un petit groupe cohérent d’actions).
- Mapper les noms d’URL sur les use-cases métier, pas sur l’implémentation technique.
- Pas de logique métier “lourde” dans les views :
  - pas de `item.objects.filter(...)` complexe,
  - pas de gros `for` avec règles métier → tout doit aller dans un service.
- Utiliser des **serializers dédiés** pour les payloads complexes, plutôt que manipuler `request.data` à la main.

---

## Application des principes SOLID, KISS et DRY

### SOLID

- **S – Single Responsibility Principle (SRP)**  
  - Chaque fichier/couche a une seule raison de changer :  
    - `api/*.py` : changement lié au contrat HTTP / format de réponse.  
    - `services/*.py` : changement de règles métier.  
    - `repositories/*.py` : changement de stratégie d’accès aux données (ORM, optimisations, index...).  
    - `models.py` : changement de structure métier / base de données.

- **O – Open/Closed Principle (OCP)**  
  - On ajoute de nouveaux comportements en **ajoutant** des services / repositories plutôt qu’en modifiant partout les anciennes views.  
  - Exemple : un nouveau type d’inventaire peut être ajouté via un **nouveau service** et une **nouvelle vue API**, sans casser les anciens endpoints.

- **L – Liskov Substitution Principle (LSP)**  
  - Les vues héritent d’`APIView` / `ServerSideDataTableView` et respectent leur contrat (mêmes méthodes HTTP, même type de réponse).  
  - Les services sont des fonctions ou classes indépendantes que l’on peut remplacer facilement par d’autres implémentations (tests, mocks).

- **I – Interface Segregation Principle (ISP)**  
  - Les repositories exposent des **fonctions ciblées** (`list_items_by_emplacement`, `get_inventaire_by_id`) plutôt qu’une grosse “interface” qui fait tout.  
  - Les serializers sont spécialisés (input / output) pour éviter de surcharger un seul serializer avec tous les cas.

- **D – Dependency Inversion Principle (DIP)**  
  - Les vues dépendent des **services** (abstraction métier) plutôt que des models directement.  
  - Les services dépendent de **repositories** (abstraction d’accès aux données) plutôt que d’appels ORM dispersés.

### KISS (Keep It Simple, Stupid)

- Découpage par **domaine fonctionnel** (articles, items, inventaires, tags, opérations) pour garder des fichiers lisibles.  
- Préférer des services/fonctions courts et explicites à des vues énormes avec des dizaines de branches `if/else`.  
- Limiter le nombre de responsabilités par fichier/classe pour faciliter la compréhension d’un nouveau développeur.

### DRY (Don’t Repeat Yourself)

- Centraliser :
  - La logique métier commune dans `services/*.py` (ex: calcul de “manquant / intru / correcte” pour l’inventaire).  
  - Les accès base réutilisables dans `repositories/*.py` (ex: `list_items_by_emplacement`).  
  - Les schémas de données dans des serializers réutilisables si plusieurs endpoints renvoient le même format.
- Éviter de copier-coller du code entre plusieurs vues :
  - Une règle métier ne doit exister qu’à **un seul endroit** (un service).  
  - Une requête ORM complexe ne doit pas être dupliquée dans 5 vues différentes mais extraite dans un repository.

Concrètement, à chaque fois que tu ajoutes une nouvelle fonctionnalité :

- **Tu pars du besoin métier** → tu crées (ou réutilises) un **service**.  
- Tu regardes si une requête ORM similaire existe déjà dans un **repository** → sinon tu l’ajoutes là.  
- Tu exposes ce service via une **vue** qui reste très fine (validation + appel service + sérialisation).  
- Tu gardes ainsi une base de code **SOLID, simple (KISS) et sans duplication (DRY)**.

---

## Résumé

- L’architecture cible est : **View → Serializer → Service → Repository → Model**.
- `masterdata/views.py` doit être **découpé par domaine** dans `masterdata/api/`.
- La logique métier doit être déplacée dans `masterdata/services/`.
- Les accès à la base doivent être centralisés dans `masterdata/repositories/`.
- La migration peut se faire **progressivement**, vue par vue, sans casser les URLs existantes.


