"""
Utilitaire pour la gestion des filtres par date dans les APIs KPI

Ce module fournit des fonctions utilitaires pour gérer les filtres de date
avec tous les opérateurs (exact, between, gte, lte, etc.) dans les APIs KPI.

Fonctionnalités:
- Parsing des dates depuis les paramètres de requête
- Construction de filtres Q Django pour les dates
- Support de tous les opérateurs de comparaison
- Gestion des erreurs et validation
"""

from django.db.models import Q
from django.utils.dateparse import parse_date, parse_datetime
import logging

logger = logging.getLogger(__name__)


class DateFilterHelper:
    """
    Classe utilitaire pour gérer les filtres par date avec tous les opérateurs
    """
    
    @staticmethod
    def parse_date_filter(date_str):
        """Parse une date depuis une chaîne de caractères"""
        if not date_str:
            return None
        
        # Essayer de parser comme date
        parsed_date = parse_date(date_str)
        if parsed_date:
            return parsed_date
        
        # Essayer de parser comme datetime
        parsed_datetime = parse_datetime(date_str)
        if parsed_datetime:
            return parsed_datetime.date()
        
        return None
    
    @staticmethod
    def build_date_filter(field_name, date_value, operator='exact'):
        """
        Construit un filtre Q pour un champ de date
        
        Args:
            field_name: Nom du champ de date (ex: 'date_achat')
            date_value: Valeur de date (peut être une chaîne ou un objet date)
            operator: Opérateur de comparaison ('exact', 'gte', 'lte', 'gt', 'lt', 'between')
        
        Returns:
            Q object pour le filtre
        """
        if not date_value:
            return Q()
        
        # Parser la date si c'est une chaîne
        if isinstance(date_value, str):
            parsed_date = DateFilterHelper.parse_date_filter(date_value)
            if not parsed_date:
                logger.warning(f"Impossible de parser la date: {date_value}")
                return Q()
            date_value = parsed_date
        
        # Construire le filtre selon l'opérateur
        if operator == 'exact':
            return Q(**{field_name: date_value})
        elif operator == 'gte':
            return Q(**{f"{field_name}__gte": date_value})
        elif operator == 'lte':
            return Q(**{f"{field_name}__lte": date_value})
        elif operator == 'gt':
            return Q(**{f"{field_name}__gt": date_value})
        elif operator == 'lt':
            return Q(**{f"{field_name}__lt": date_value})
        elif operator == 'between':
            # Pour 'between', date_value doit être une liste [date_debut, date_fin]
            if isinstance(date_value, list) and len(date_value) == 2:
                start_date = DateFilterHelper.parse_date_filter(date_value[0])
                end_date = DateFilterHelper.parse_date_filter(date_value[1])
                if start_date and end_date:
                    return Q(**{f"{field_name}__gte": start_date, f"{field_name}__lte": end_date})
            return Q()
        elif operator == 'year':
            return Q(**{f"{field_name}__year": date_value})
        elif operator == 'month':
            return Q(**{f"{field_name}__month": date_value})
        elif operator == 'day':
            return Q(**{f"{field_name}__day": date_value})
        else:
            logger.warning(f"Opérateur de date non reconnu: {operator}")
            return Q()
    
    @staticmethod
    def extract_date_filters_from_params(params):
        """
        Extrait tous les filtres de date des paramètres de requête
        
        Args:
            params: QueryDict des paramètres de requête
        
        Returns:
            dict: Dictionnaire des filtres de date organisés par champ
        """
        date_filters = {}
        
        # Champs de date disponibles
        date_fields = [
            'date_achat', 'date_reception', 'date_affectation', 'date_archive',
            'date_creation', 'date_debut', 'date_fin', 'created_at', 'updated_at'
        ]
        
        # Opérateurs supportés
        operators = ['exact', 'gte', 'lte', 'gt', 'lt', 'between', 'year', 'month', 'day']
        
        for field in date_fields:
            for operator in operators:
                param_name = f"{field}_{operator}"
                if param_name in params:
                    value = params[param_name]
                    
                    if operator == 'between':
                        # Pour 'between', on attend deux dates séparées par une virgule
                        if ',' in value:
                            dates = [d.strip() for d in value.split(',')]
                            if len(dates) == 2:
                                date_filters[param_name] = {
                                    'field': field,
                                    'operator': operator,
                                    'value': dates
                                }
                    else:
                        date_filters[param_name] = {
                            'field': field,
                            'operator': operator,
                            'value': value
                        }
        
        return date_filters
    
    @staticmethod
    def apply_date_filters_to_queryset(queryset, date_filters):
        """
        Applique les filtres de date à un queryset
        
        Args:
            queryset: Queryset Django
            date_filters: Dictionnaire des filtres de date
        
        Returns:
            Queryset filtré
        """
        # Obtenir le modèle du queryset
        model = queryset.model
        
        # Mapping des champs de date selon le modèle
        field_mapping = {
            'TransferHistorique': {
                'date_achat': 'created_at',
                'date_reception': 'created_at',
                'date_affectation': 'created_at',
            }
        }
        
        model_name = model.__name__
        mapping = field_mapping.get(model_name, {})
        
        for filter_name, filter_data in date_filters.items():
            field = filter_data['field']
            operator = filter_data['operator']
            value = filter_data['value']
            
            # Appliquer le mapping si nécessaire
            mapped_field = mapping.get(field, field)
            
            # Vérifier si le champ existe dans le modèle
            try:
                # Essayer d'accéder au champ pour vérifier son existence
                _ = model._meta.get_field(mapped_field)
                
                date_filter = DateFilterHelper.build_date_filter(mapped_field, value, operator)
                if date_filter:
                    queryset = queryset.filter(date_filter)
            except Exception as e:
                logger.warning(f"Champ de date '{mapped_field}' non trouvé dans le modèle {model_name}: {str(e)}")
                continue
        
        return queryset
    
    @staticmethod
    def get_supported_date_fields():
        """
        Retourne la liste des champs de date supportés
        
        Returns:
            list: Liste des champs de date supportés
        """
        return [
            'date_achat', 'date_reception', 'date_affectation', 'date_archive',
            'date_creation', 'date_debut', 'date_fin', 'created_at', 'updated_at'
        ]
    
    @staticmethod
    def get_supported_operators():
        """
        Retourne la liste des opérateurs supportés
        
        Returns:
            list: Liste des opérateurs supportés
        """
        return ['exact', 'gte', 'lte', 'gt', 'lt', 'between', 'year', 'month', 'day']
    
    @staticmethod
    def get_date_filter_examples():
        """
        Retourne des exemples d'utilisation des filtres de date
        
        Returns:
            dict: Exemples d'utilisation
        """
        return {
            'exact': 'date_achat_exact=2024-01-15',
            'gte': 'date_achat_gte=2024-01-01',
            'lte': 'date_achat_lte=2024-12-31',
            'between': 'date_achat_between=2024-01-01,2024-12-31',
            'year': 'date_achat_year=2024',
            'month': 'date_achat_month=1',
            'day': 'date_achat_day=15',
            'multiple': 'date_achat_gte=2024-01-01&date_achat_lte=2024-12-31&created_at_year=2024'
        }
