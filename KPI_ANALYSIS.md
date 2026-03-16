# Analyse des KPIs - Valeur et Quantité

## 📊 KPIs Basés sur la Quantité

### 1. Articles
- **Total Articles** : Nombre total d'articles achetés
- **Articles par Fournisseur** : Quantité d'articles par fournisseur
- **Articles par Famille** : Quantité d'articles par famille
- **Articles par Catégorie** : Quantité d'articles par catégorie
- **Articles par Nature** : Quantité d'articles par nature
- **Articles par Marque** : Quantité d'articles par marque


### 2. Items
- **Items Affectés** : Nombre d'items avec statut "affecter"
- **Items Non Affectés** : Nombre d'items avec statut "non affecter"
- **Items Archivés** : Nombre d'items archivés (`archive = True`)
- **Items par Département** : Répartition des items par département
- **Items par Emplacement** : Répartition des items par emplacement
- **Items par Zone** : Via `emplacement.zone`
- **Items par Location** : Via `emplacement.zone.location`

- **Items par Personne** : Nombre d'items affectés à chaque personne

### 3. Emplacements & Localisations
- **Total Locations** : Nombre de sites/locaux
- **Total Zones** : Nombre de zones
- **Total Emplacements** : Nombre d'emplacements
- **Emplacements par Zone** : Répartition des emplacements par zone
- **Zones par Location** : Répartition des zones par location
- **Emplacements avec Tag** : Nombre d'emplacements ayant un tag

### 4. Tags

- **Tags Disponibles** : Tags avec `affecter = False`
- **Tags par Type** : Répartition par type de tag

### 5. Inventaires
- **Total Inventaires** : Nombre total de campagnes d'inventaire
- **Inventaires par Catégorie** : Location, Zone, Département, Emplacement
- **Inventaires Terminés** : Statut "Terminer"
- **Inventaires En Cours** : Statut "En cours"
- **Inventaires En Attente** : Statut "En attente"


- **Taux de Complétion** : `(Emplacements terminés / Total emplacements) * 100`
- **Items Inventoriés** : Nombre total d'items dans `detail_inventaire`
- **Items par État** : Répartition des items par état dans l'inventaire

### 6. Personnes
- **Personnes avec Affectations** : Personnes ayant au moins un item

### 7. Fournisseurs & Départements
- **Total Fournisseurs** : Nombre de fournisseurs
- **Total Départements** : Nombre de départements

### 8. Transferts & Archives with Date
- **Total Transferts** : Nombre d'opérations de transfert
- **Transferts par Item** : Nombre de transferts pour chaque item
- **Transferts d'Emplacement** : Nombre de changements d'emplacement
- **Transferts de Personne** : Nombre de changements d'affectation
- **Transferts de Département** : Nombre de changements de département
- **Total Items Archivés** : Nombre d'enregistrements dans `ArchiveItem`

## 💰 KPIs Basés sur la Valeur with date

### 1. Valeur des Articles
- **Valeur Totale des Achats** : `SUM(prix_achat * qte)`
- **Valeur par Fournisseur** : `SUM(prix_achat * qte)` groupé par fournisseur
- **Valeur par Produit/Famille** : `SUM(prix_achat * qte)` groupé par produit
- **Valeur par Catégorie** : `SUM(prix_achat * qte)` groupé par catégorie
- **Valeur par Nature** : `SUM(prix_achat * qte)` groupé par nature
- **Valeur par Marque** : `SUM(prix_achat * qte)` groupé par marque
- **Valeur par Département** : Valeur des items par département
- **Valeur par Location** : Valeur des items par site
- **Valeur par Zone** : Valeur des items par zone
- **Valeur par Emplacement** : Valeur des items par emplacement

### 2. Valeur Résiduelle (Amortissement)
- **Valeur Résiduelle Totale** : `SUM(item.calculate_residual_value())`
- **Valeur Résiduelle par Département** : Valeur résiduelle groupée par département
- **Valeur Résiduelle par Emplacement** : Valeur résiduelle groupée par emplacement
- **Valeur Résiduelle par Famille** : Valeur résiduelle groupée par produit
- **Valeur Amortie** : `Valeur d'achat - Valeur résiduelle`
- **Taux d'Amortissement** : `(Valeur amortie / Valeur d'achat) * 100`

### 3. Valeur des Opérations
- **Valeur Totale des Opérations** : `SUM(operation_article.prix)`
- **Valeur des Opérations par Item** : Coût total des opérations par item
- **Valeur des Opérations par Type** : Groupé par type d'opération

## 📈 KPIs Combinés (Valeur + Quantité)

### 1. Performance d'Achat
```sql
- Prix Moyen par Article
- Quantité Moyenne par Commande
- Valeur Totale par Facture
- Nombre d'Articles par Facture
```

### 2. Performance d'Inventaire
```sql
- Taux de Couverture: (Items inventoriés / Total items) * 100
- Valeur Inventoriée vs Valeur Totale
- Écarts d'Inventaire (Quantité & Valeur)
```

### 3. Performance de Gestion
```sql
- Coût Moyen par Item
- Nombre d'Items par m² (si surface disponible)
- Rotation des Items (Transferts / Période)
- Taux d'Utilisation des Tags: (Tags affectés / Total tags) * 100
```

### 4. Analyses Temporelles
```sql
- Évolution des Achats par Mois/Trimestre/Année
- Évolution de la Valeur du Parc
- Évolution du Taux d'Affectation
- Délai Moyen entre Achat et Réception
- Durée Moyenne des Inventaires
- Taux d'Archive par Période
```

---

## 🎯 KPIs Critiques Recommandés

### Dashboard Principal
1. **Valeur Totale du Parc** : Somme de tous les prix d'achat
2. **Valeur Résiduelle Totale** : Valeur après amortissement
3. **Nombre Total d'Items** : Quantité totale d'actifs
4. **Taux d'Affectation** : % d'items affectés
5. **Nombre d'Inventaires En Cours** : Inventaires actifs
6. **Valeur par Département** : Top 5 départements

### Dashboard Achats
1. **Valeur des Achats (Période)** : Mois/Trimestre/Année
2. **Nombre d'Articles Achetés (Période)**
3. **Top 5 Fournisseurs** : Par valeur et quantité
4. **Écart Commandé vs Reçu** : Quantité et pourcentage
5. **Délai Moyen de Réception**

### Dashboard Inventaire
1. **Taux de Complétion** : % emplacements terminés
2. **Nombre d'Items Scannés**
3. **Valeur Inventoriée**
4. **Écarts Détectés** : Items manquants/trouvés
5. **Performance par Opérateur**

### Dashboard Localisation
1. **Valeur par Location** : Répartition géographique
2. **Occupation des Emplacements** : Taux d'utilisation
3. **Items par Zone** : Densité d'occupation
4. **Emplacements sans Tag** : À équiper

### Dashboard Finances
1. **Valeur d'Acquisition Totale**
2. **Valeur Résiduelle Totale**
3. **Amortissement Total**
4. **Coût des Opérations** : Maintenance, réparations
5. **ROI par Catégorie** : Si données revenus disponibles

---

## 🔍 Requêtes SQL Suggérées

### 1. Valeur Totale du Parc
```python
from django.db.models import Sum, F

total_value = article.objects.aggregate(
    total=Sum(F('prix_achat') * F('qte'))
)['total']
```

### 2. Valeur Résiduelle Totale
```python
from django.db.models import Sum

items_list = item.objects.select_related('article__produit').all()
total_residual = sum(i.calculate_residual_value() or 0 for i in items_list)
```

### 3. Taux d'Affectation
```python
from django.db.models import Count, Q

stats = item.objects.aggregate(
    total=Count('id'),
    affectes=Count('id', filter=Q(statut='affecter'))
)
taux = (stats['affectes'] / stats['total'] * 100) if stats['total'] > 0 else 0
```

### 4. Top 5 Fournisseurs par Valeur
```python
from django.db.models import Sum, F

top_fournisseurs = fournisseur.objects.annotate(
    total_value=Sum(F('article__prix_achat') * F('article__qte'))
).order_by('-total_value')[:5]
```

### 5. Valeur par Département
```python
from django.db.models import Sum, F

dept_values = departement.objects.annotate(
    total_value=Sum(F('item__article__prix_achat'))
).order_by('-total_value')
```

### 6. Performance Inventaire
```python
from django.db.models import Count, Q

inv_stats = inventaire.objects.filter(id=inv_id).annotate(
    total_emplacements=Count('inventaire_emplacement'),
    emplacements_termines=Count('inventaire_emplacement', 
                                 filter=Q(inventaire_emplacement__statut='Terminer'))
)
```

### 7. Évolution des Achats par Mois
```python
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth

monthly_purchases = article.objects.annotate(
    month=TruncMonth('date_achat')
).values('month').annotate(
    total_value=Sum(F('prix_achat') * F('qte')),
    total_qty=Sum('qte')
).order_by('month')
```

### 8. Items par Location avec Valeur
```python
from django.db.models import Count, Sum, F

location_stats = location.objects.annotate(
    nb_items=Count('zone__emplacement__item'),
    total_value=Sum(F('zone__emplacement__item__article__prix_achat'))
).order_by('-total_value')
```

---

## 📊 Recommandations d'Implémentation

### 1. Créer une Vue API pour les KPIs
```python
# masterdata/Views/KPIView.py
class KPIDashboardAPIView(APIView):
    """
    Retourne tous les KPIs principaux pour le dashboard
    """
    def get(self, request):
        # Calculer tous les KPIs
        # Retourner en JSON
        pass
```

### 2. Utiliser le Cache
```python
from django.core.cache import cache

def get_kpi_total_value():
    cache_key = 'kpi_total_value'
    value = cache.get(cache_key)
    if value is None:
        value = calculate_total_value()
        cache.set(cache_key, value, 3600)  # 1 heure
    return value
```

### 3. Créer des Signaux pour Mise à Jour Auto
```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=item)
def invalidate_kpi_cache(sender, instance, **kwargs):
    cache.delete_pattern('kpi_*')
```

### 4. Ajouter des Index pour Performance
```python
class item(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['statut', 'archive']),
            models.Index(fields=['departement', 'emplacement']),
        ]
```

---

## 💡 KPIs Additionnels Possibles

Si vous ajoutez ces champs aux modèles:

1. **Surface (m²)** aux emplacements → Densité de valeur/m²
2. **Budget** aux départements → Taux d'utilisation du budget
3. **Prix de Vente** aux items → Marge bénéficiaire
4. **État de Fonctionnement** aux items → Taux de disponibilité
5. **Coût de Maintenance** → Coût total de possession (TCO)
6. **Date de Garantie** → Items sous garantie vs hors garantie

---

Cette analyse couvre tous les KPIs extraibles de votre base de données actuelle. 
Souhaitez-vous que j'implémente certains de ces KPIs dans une API dédiée?

