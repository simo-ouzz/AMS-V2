## API Batch d’archivage des items

### Description

Cette API permet d’**archiver plusieurs items en une seule requête** HTTP, à partir d’un tableau d’identifiants `items_id`.

L’API :
- met à jour le champ `archive` des items ciblés,
- crée les enregistrements d’historique `ArchiveItem` si nécessaire,
- ne ré-archive pas les items déjà archivés (ils sont comptés dans `already_archived`).

---

### Endpoint

- **Méthode**: `POST`  
- **URL**: `/items/archive/batch/`
- **Authentification**: **JWT** obligatoire  
  - Header: `Authorization: Bearer <access_token>`

---

### Corps de la requête (JSON)

```json
{
  "items_id": [1, 2, 3]
}
```

- **`items_id`** (obligatoire) :
  - Type: `array` d’entiers
  - Description: liste des `id` des items à archiver.

---

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

---

### Codes de statut possibles

- **200 OK** : traitement terminé (avec ou sans erreurs partielles, détaillées dans `errors`).
- **401 Unauthorized** : token manquant ou invalide.
- **403 Forbidden** : utilisateur non authentifié ou non autorisé.
- **500 Internal Server Error** : erreur serveur imprévue.

---

### Exemple d’appel (cURL)

```bash
curl -X POST "https://<host>/masterdata/items/archive/batch/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "items_id": [10, 11, 12]
  }'
```

