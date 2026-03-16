## APIs d’archivage des items

Ce document regroupe la documentation des deux APIs d’archivage des items :

- **Batch JSON** : `POST /items/archive/batch/`
- **Import Excel** : `POST /items/archive/import-excel/`

---

## 1. API Batch d’archivage des items

### Description

Cette API permet d’**archiver plusieurs items en une seule requête** HTTP, à partir d’un tableau d’identifiants `items_id`.

L’API :
- met à jour le champ `archive` des items ciblés,
- crée les enregistrements d’historique `ArchiveItem` si nécessaire,
- ne ré-archive pas les items déjà archivés (ils sont comptés dans `already_archived`).

### Endpoint

- **Méthode**: `POST`  
- **URL**: `/items/archive/batch/`
- **Authentification**: **JWT** obligatoire  
  - Header: `Authorization: Bearer <access_token>`

### Corps de la requête (JSON)

```json
{
  "items_id": [1, 2, 3]
}
```

- **`items_id`** (obligatoire) :
  - Type: `array` d’entiers
  - Description: liste des `id` des items à archiver.

### Réponse (200 OK)

Corps de réponse JSON :

```json
{
  "total": 3,
  "success": 3,
  "already_archived": 1,
  "not_found": 0,
  "errors": []
}
```

- **`total`**: nombre total d’identifiants reçus.
- **`success`**: nombre d’items traités avec succès (inclut ceux déjà archivés).
- **`already_archived`**: nombre d’items qui étaient déjà archivés avant l’appel.
- **`not_found`**: nombre d’identifiants ne correspondant à aucun item.
- **`errors`**: tableau de messages d’erreur textuels (ex. `Item avec id=9999 introuvable.`).

### Codes de statut possibles

- **200 OK** : traitement terminé (avec ou sans erreurs partielles, détaillées dans `errors`).
- **401 Unauthorized** : token manquant ou invalide.
- **403 Forbidden** : utilisateur non authentifié ou non autorisé.
- **500 Internal Server Error** : erreur serveur imprévue.

### Exemple d’appel (cURL)

```bash
curl -X POST "https://<host>/masterdata/items/archive/batch/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "items_id": [10, 11, 12]
  }'
```

---

## 2. API d’import Excel pour l’archivage des items

### Description

Cette API permet d’**archiver des items en masse à partir d’un fichier Excel (.xlsx)**.  
Chaque ligne du fichier indique le **tag** d’un item à archiver, et éventuellement sa **désignation** et un **commentaire** associé.

L’API :
- archive les items non encore archivés,
- **ne ré-archive pas** les items déjà archivés (comptés dans `already_archived`),
- retourne des statistiques détaillées (succès, déjà archivés, introuvables, erreurs).

### Endpoint

- **Méthode**: `POST`  
- **URL**: `/items/archive/import-excel/`
- **Authentification**: **JWT** obligatoire  
  - Header: `Authorization: Bearer <access_token>`
- **Type de requête**: `multipart/form-data`

### Paramètres de la requête

Corps `multipart/form-data` :

- **`file`** (obligatoire)
  - Type: fichier `.xlsx`
  - Description: fichier Excel contenant les items à archiver.

- **`skip_errors`** (optionnel)
  - Type: booléen (`true`/`false`)
  - Défaut: `false`
  - `false` : **tout ou rien** → s’il y a au moins une erreur, aucun item n’est archivé et la requête retourne `400` avec la liste complète des erreurs.
  - `true` : mode tolérant → les items valides sont archivés, les erreurs sont listées dans `errors` mais la requête retourne `200`.

### Format attendu du fichier Excel

- La **première ligne** du fichier doit contenir les en-têtes de colonnes.
- Colonnes **obligatoires** :
  - `tag` : référence du tag associé à l’item (`item.tag.reference`).
- Colonnes **optionnelles** :
  - `designation` : désignation de l’article (`item.article.designation`), utilisée à titre de contrôle (cohérence).
  - `commentaire` : texte qui sera stocké dans `ArchiveItem.commentaire` pour cet item.

Exemple de contenu :

| tag        | designation                 | commentaire                 |
|-----------|-----------------------------|-----------------------------|
| TAG-00010 | PC Portable Lenovo ThinkPad | Sortie de parc informatique |
| TAG-00011 | Écran Dell 24"              | Cassé / hors service        |
| TAG-00012 | Imprimante HP LaserJet      | Don                         |

Règles par ligne :

- Si `tag` est vide → ligne ignorée.
- Si aucun item ne correspond au `tag` (pour le compte de l’utilisateur) → compté dans `not_found`, message dans `errors`.
- Si `designation` est fournie et ne correspond pas à la désignation en base → un message d’incohérence est ajouté dans `errors` (mais l’archivage peut tout de même se faire si l’item est trouvé).
- Si l’item est déjà archivé → compté dans `already_archived`.
- Sinon → archivage de l’item + création d’un `ArchiveItem`.

### Réponse (200 OK)

Corps de réponse JSON (mode tolérant `skip_errors=true`) :

```json
{
  "total": 10,
  "success": 8,
  "already_archived": 1,
  "not_found": 1,
  "errors": [
    "Ligne 5: Item avec tag='TAG-9999' introuvable pour ce compte."
  ]
}
```

- **`total`**: nombre de lignes valides (tag non vide) traitées.
- **`success`**: nombre d’items effectivement archivés.
- **`already_archived`**: items déjà archivés avant l’import.
- **`not_found`**: nombres de `tag` qui ne correspondent à aucun item existant pour le compte.
- **`errors`**: messages d’erreur détaillés, **préfixés par le numéro de la ligne Excel** (`Ligne X:`).

### Réponse (400 Bad Request – mode tout ou rien)

Si `skip_errors=false` (par défaut) et qu’au moins une erreur est détectée, **aucun item n’est archivé** et l’API retourne :

```json
{
  "errors": [
    "Ligne 5: Item avec tag='TAG-00010' introuvable pour ce compte.",
    "Ligne 6: Incohérence de désignation pour tag='TAG-00011' (fichier='PC LENOVO', base='PC Portable Lenovo ThinkPad')."
  ]
}
```

### Codes de statut possibles

- **200 OK** : import terminé (même avec erreurs si `skip_errors=true`).
- **400 Bad Request** : problème de format de fichier ou de contenu (par ex. colonne `tag` manquante) **ou** erreurs fonctionnelles en mode tout ou rien (`skip_errors=false`).
- **401 Unauthorized** : token manquant ou invalide.
- **403 Forbidden** : utilisateur non authentifié ou non autorisé.
- **500 Internal Server Error** : erreur serveur imprévue.

### Exemple d’appel (cURL)

```bash
curl -X POST "https://<host>/masterdata/items/archive/import-excel/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@/chemin/vers/fichier.xlsx" \
  -F "skip_errors=false"
```

