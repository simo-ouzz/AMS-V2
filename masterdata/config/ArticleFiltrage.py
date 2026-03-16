from django_filters import rest_framework as filters
from masterdata.models import article  # Adjust the import according to your app structure
from django.db.models import Q
import django_filters


class ArticleFilter(filters.FilterSet):
    # Filtres Django Filter classiques
    code_article = django_filters.CharFilter(field_name='code_article', lookup_expr='icontains')
    designation = django_filters.CharFilter(field_name='designation', lookup_expr='icontains')
    fournisseur = django_filters.CharFilter(field_name='fournisseur__nom', lookup_expr='icontains')
    prix_achat = django_filters.NumberFilter(field_name='prix_achat', lookup_expr='exact')
    date_achat = django_filters.DateFilter(field_name='date_achat', lookup_expr='exact')
    famille = django_filters.CharFilter(field_name='produit__libelle', lookup_expr='icontains')
    categorie = django_filters.CharFilter(field_name='produit__categorie__libelle', lookup_expr='icontains')
    date_reception = django_filters.DateFilter(field_name="date_reception", lookup_expr='exact')
    
    # Support des filtres avec lookup explicite (pour compatibilité)
    code_article__icontains = django_filters.CharFilter(field_name='code_article', lookup_expr='icontains')
    designation__icontains = django_filters.CharFilter(field_name='designation', lookup_expr='icontains')
    fournisseur__nom__icontains = django_filters.CharFilter(field_name='fournisseur__nom', lookup_expr='icontains')
    produit__libelle__icontains = django_filters.CharFilter(field_name='produit__libelle', lookup_expr='icontains')
    produit__categorie__libelle__icontains = django_filters.CharFilter(field_name='produit__categorie__libelle', lookup_expr='icontains')
    
    class Meta:
        model = article
        fields = [
            'date_reception', 'code_article', 'designation', 'date_achat', 'fournisseur', 
            'N_facture', 'famille', 'prix_achat', 'categorie',
            'code_article__icontains', 'designation__icontains', 'fournisseur__nom__icontains',
            'produit__libelle__icontains', 'produit__categorie__libelle__icontains'
        ]  


