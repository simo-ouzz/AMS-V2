import django_filters
from masterdata.models import item, Personne, emplacement, departement
from django.db.models import Q

class ItemFilter(django_filters.FilterSet):
    # Filtrage pour les articles
    code_article = django_filters.CharFilter(field_name='article__code_article', lookup_expr='icontains')
    designation = django_filters.CharFilter(field_name='article__designation', lookup_expr='icontains')
    fournisseur = django_filters.CharFilter(field_name='article__fournisseur__nom', lookup_expr='icontains')
    prix_achat = django_filters.NumberFilter(field_name='article__prix_achat', lookup_expr='exact')
    date_achat = django_filters.DateFilter(field_name='article__date_achat', lookup_expr='exact')
    departement = django_filters.CharFilter(field_name='departement__nom', lookup_expr='icontains')
    famille = django_filters.CharFilter(field_name='article__produit__libelle', lookup_expr='icontains')
    emplacement = django_filters.CharFilter(field_name='emplacement__nom', lookup_expr='icontains')
    location = django_filters.CharFilter(field_name='emplacement__zone__location__nom', lookup_expr='icontains')
    zone = django_filters.CharFilter(field_name='emplacement__zone__nom', lookup_expr='icontains')
    affectation_personne_nom = django_filters.CharFilter(field_name='affectation_personne__nom', lookup_expr='icontains')
    affectation_personne_prenom = django_filters.CharFilter(field_name='affectation_personne__prenom', lookup_expr='icontains')
    
    # Filtre pour le nom complet (nom + prenom)
    affectation_personne_full_name_exact = django_filters.CharFilter(method='filter_full_name_exact')
    affectation_personne_full_name_icontains = django_filters.CharFilter(method='filter_full_name_icontains')
    categorie = django_filters.CharFilter(field_name='article__produit__categorie__libelle', lookup_expr='icontains')
    date_reception = django_filters.DateFilter(field_name="article__date_reception", lookup_expr='exact')
    n_facture = django_filters.DateFilter(field_name="article__N_facture", lookup_expr='exact')


    class Meta:
        model = item
        fields = ['code_article', 'n_facture','designation', 'fournisseur', 'prix_achat', 'date_achat', 'departement', 'emplacement', 'affectation_personne_nom', 'famille','affectation_personne_prenom','affectation_personne_full_name_exact','affectation_personne_full_name_icontains','categorie','location','zone']

    def filter_full_name_exact(self, queryset, name, value):
        """Filtre par nom complet exact (nom + prenom)"""
        if not value:
            return queryset
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Filtre nom complet exact: '{value}'")
        
        # Normaliser les espaces et caractères spéciaux
        value = value.replace('+', ' ').strip()
        logger.debug(f"Valeur normalisée: '{value}'")
        
        # Utiliser CONCAT pour chercher dans le nom complet
        from django.db.models import Value, F
        from django.db.models.functions import Concat
        
        result = queryset.annotate(
            full_name=Concat(
                F('affectation_personne__nom'),
                Value(' '),
                F('affectation_personne__prenom')
            )
        ).filter(full_name__iexact=value)
        
        logger.debug(f"Résultat filtre nom complet: {result.count()} éléments")
        return result

    def filter_full_name_icontains(self, queryset, name, value):
        """Filtre par nom complet contenant (nom + prenom)"""
        if not value:
            return queryset
        
        # Normaliser les espaces et caractères spéciaux
        value = value.replace('+', ' ').strip()
        
        # Utiliser CONCAT pour chercher dans le nom complet
        from django.db.models import Value, F
        from django.db.models.functions import Concat
        return queryset.annotate(
            full_name=Concat(
                F('affectation_personne__nom'),
                Value(' '),
                F('affectation_personne__prenom')
            )
        ).filter(full_name__icontains=value)
