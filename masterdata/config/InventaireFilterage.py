from django_filters import rest_framework as filters
from masterdata.models import inventaire  # Ajustez l'import selon la structure de votre application
from django.db.models import Q


class InventaireFilter(filters.FilterSet):
    search = filters.CharFilter(method='filter_search')  # Méthode de recherche personnalisée

    class Meta:
        model = inventaire
        fields = '__all__'

    def filter_search(self, queryset, name, value):
        # Utilisation de Q pour construire des requêtes complexes sur plusieurs champs
        return queryset.filter(
            Q(nom__icontains=value) |  # Rechercher par nom
            Q(reference__icontains=value) |  # Rechercher par référence
            Q(statut__icontains=value) |  # Rechercher par statut
            Q(categorie__icontains=value) |  # Rechercher par catégorie
            Q(user__nom__icontains=value) |  # Rechercher par nom d'utilisateur lié
            Q(user__prenom__icontains=value)  # Rechercher par prénom d'utilisateur lié
        )