## API d’import Excel pour l’archivage des items

### Description

Cette API permet d’**archiver des items en masse à partir d’un fichier Excel (.xlsx)**.  
Chaque ligne du fichier indique l’`id` d’un item à archiver, et éventuellement un `commentaire` associé.

L’API :
- archive les items non encore archivés,
- **ne ré-archive pas** les items déjà archivés (comptés dans `already_archived`),
- retourne des statistiques détaillées (succès, déjà archivés, introuvables, erreurs).

---

### Endpoint

- **Méthode**: `POST`  
- **URL**: `/items/archive/import-excel/`
- **Authentification**: **JWT** obligatoire  
  - Header: `Authorization: Bearer <access_token>`
- **Type de requête**: `multipart/form-data`

---

### Paramètres de la requête

Corps `multipart/form-data` :

- **`file`** (obligatoire)
  - Type: fichier `.xlsx`
  - Description: fichier Excel contenant les items à archiver.

- **`skip_errors`** (optionnel)
  - Type: booléen (`true`/`false`)
  - Défaut: `true`
  - `true` : l’import continue même si certaines lignes sont en erreur (les erreurs sont listées dans `errors`).
  - `false` : la première erreur stoppe l’import et lève une erreur.

---

### Format attendu du fichier Excel

- La **première ligne** du fichier doit contenir les en-têtes de colonnes.
- Colonnes **obligatoires** :
  - `id` : identifiant de l’item (`item.id`) à archiver.
- Colonnes **optionnelles** :
  - `commentaire` : texte qui sera stocké dans `ArchiveItem.commentaire` pour cet item.

Exemple de contenu :

| id  | commentaire                 |
|-----|-----------------------------|
| 10  | Sortie de parc informatique |
| 11  | Cassé / hors service        |
| 12  | Don                       |

Règles par ligne :

- Si `id` est vide → ligne ignorée.
- Si `id` ne correspond à aucun item → compté dans `not_found`, message dans `errors`.
- Si l’item est déjà archivé → compté dans `already_archived`.
- Sinon → archivage de l’item + création d’un `ArchiveItem`.

---

### Réponse (200 OK)

Corps de réponse JSON :

```json
{
  "total": 10,
  "success": 8,
  "already_archived": 1,
  "not_found": 1,
  "errors": [
    "Item avec id=9999 introuvable."
  ]
}
```

- **`total`**: nombre de lignes valides (id non vide) traitées.
- **`success`**: nombre d’items effectivement archivés.
- **`already_archived`**: items déjà archivés avant l’import.
- **`not_found`**: nombres d’`id` qui ne correspondent à aucun item existant.
- **`errors`**: messages d’erreur détaillés.

---

### Codes de statut possibles

- **200 OK** : import terminé (avec ou sans erreurs partielles).
- **400 Bad Request** : problème de format de fichier ou de contenu (par ex. colonne `id` manquante).
- **401 Unauthorized** : token manquant ou invalide.
- **403 Forbidden** : utilisateur non authentifié ou non autorisé.
- **500 Internal Server Error** : erreur serveur imprévue.

---

### Exemple d’appel (cURL)

```bash
curl -X POST "https://<host>/masterdata/items/archive/import-excel/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@/chemin/vers/fichier.xlsx" \
  -F "skip_errors=true"
```

