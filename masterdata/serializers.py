"""Serializers for the masterdata app.

This module exposes DRF serializers used by the API layer. Each serializer should
document the intent of its transformation/validation to ease maintenance.
"""
from decimal import Decimal
from urllib.parse import urljoin
from django.conf import settings
from rest_framework import serializers
from .models import *







class UserLoginSerializer(serializers.Serializer):
    """Authenticate a user by email and password.

    Returns the `UserWeb` instance upon successful validation.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = UserWeb.objects.filter(email=attrs.get('email')).first()
        if user:
            if user.check_password(attrs.get('password')):
                return user
            else:
                raise serializers.ValidationError("Mot de passe incorrect.")
        else:
            raise serializers.ValidationError("Aucun utilisateur trouvé avec cet email.")
class ProduitSerializer(serializers.ModelSerializer):
    """Read-only serializer exposing core product family fields."""
    categorie = serializers.StringRelatedField(source='categorie.libelle')  # Récupération de la catégorie

    class Meta:
        model = produit
        fields = ['id','libelle', 'code_produit', 'categorie', 'duree_amourtissement', 'statut', 'created_at', 'updated_at']

class MarqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = marque
        fields = '__all__'
        
class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = categorie
        fields = '__all__'
class ArticleSerializer(serializers.ModelSerializer):
    """Detailed article representation with computed image URL and category name."""
    image_url = serializers.SerializerMethodField()  
    date_reception = serializers.SerializerMethodField()
    categorie = serializers.CharField(source='produit.categorie.libelle', read_only=True)
    fournisseur = serializers.CharField(source='fournisseur.nom', read_only=True)
    class Meta:
        model = article  # Assurez-vous que le nom de votre modèle est correct
        fields = '__all__'  # Ou spécifiez les champs que vous souhaitez inclure
    def get_date_reception(self, obj):
        # Vérifiez si date_reception est un datetime et convertissez-le en date
        if isinstance(obj.date_reception, datetime):
            return obj.date_reception.date()  # Convertit datetime en date
        return obj.date_reception 
    def get_image_url(self, obj):
        
        if obj.image:  
            return obj.image.url  
        return None  
        
class EditArticleSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()  # Champ pour l'URL de l'image

    class Meta:
        model = article
        fields = '__all__'  # Inclut tous les champs du modèle

    def get_image_url(self, obj):
        request = self.context.get('request')  # Obtient la requête pour construire l'URL absolue
        if obj.image:
            return request.build_absolute_uri(obj.image.url)  # Crée l'URL complète 
        return None  # Renvoie None si l'image n'existe pas
from datetime import datetime

class ArticleSerializeres(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    produit = serializers.CharField(source='produit.libelle', read_only=True)  # Obtenir le libellé du produit
    statut = serializers.SerializerMethodField()  # Ajouter le statut comme un champ calculé
    fournisseur = serializers.CharField(source='fournisseur.nom', read_only=True)
    nature = serializers.CharField(source='nature.libelle', read_only=True)
    marque = serializers.CharField(source='marque.nom', read_only=True)
    categorie = serializers.CharField(source='produit.categorie.libelle', read_only=True)  # Correction ici


    class Meta:
        model = article
        fields = [
            'id', 'produit', 'nature', 'statut', 'fournisseur', 'image_url', 'categorie',
            'code_article', 'designation', 'date_achat', 'numero_comptable',
            'couleur', 'poids', 'volume', 'langueur', 'hauteur', 'largeur',
            'date_expiration', 'date_peremption', 'date_reception',
            'prix_achat', 'attachement1', 'attachement2', 'marque', 
            'N_facture', 'attachement3', 'qte_recue', 'qte', 'created_at', 'updated_at'
        ]

    def get_statut(self, obj):
        return obj.produit.statut

    def get_image_url(self, obj):
        if obj.image:  # Assurez-vous que 'image' est le champ correct dans votre modèle
            # Concatène le SITE_URL avec le chemin de l'image
            return urljoin(settings.SITE_URL, obj.image.url)  
        return None # Retourne None si aucune image n'est disponible

    def get_fournisseur(self, obj):
        return obj.fournisseur.nom

class EditItemArticleSerializer(serializers.ModelSerializer):
    categorie = serializers.SerializerMethodField()



    class Meta:
        model = article
        fields = [
            'produit', 'nature', 'fournisseur',  'categorie', 'marque','N_facture'
        ]
    def get_categorie(self, obj):
    # Récupérer la catégorie via le produit de l'article
        if obj.produit and obj.produit.categorie:
            return obj.produit.categorie.id
        return None



class EditItemSerializer(serializers.ModelSerializer):
    article = EditItemArticleSerializer()  # Assurez-vous que cela fonctionne
    
    class Meta:
        model = item
        fields = [
         
            'article',
            
        ]

    
    def get_produit_categorie(self, obj):
        # Récupérer la catégorie via l'article et le produit
        if obj.article and obj.article.produit:
            return obj.article.produit.categorie.libelle  # Assurez-vous que cela correspond à la structure de vos modèles
        return None
    

from datetime import datetime

class CreateOneArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = article
        fields = [
            'id', 'produit', 'nature', 'fournisseur', 'image',
             'designation', 'date_achat', 'numero_comptable',
            'couleur', 'poids', 'volume', 'langueur', 'hauteur', 'largeur',
            'date_expiration', 'date_peremption', 'date_reception',
            'prix_achat', 'attachement1', 'attachement2', 'marque',
            'N_facture', 'attachement3', 'qte',
        ]
    extra_kwargs = {'user': {'read_only': True}}

    # def validate_produit(self, value):
    #     # Essayer de convertir le produit en entier
    #     try:
    #         return int(value)
    #     except (ValueError, TypeError):
    #         raise serializers.ValidationError("Le produit doit être un nombre entier.")

    def create(self, validated_data):
        # Si qte n'est pas dans validated_data, on lui donne la valeur par défaut
        if 'qte' not in validated_data or validated_data['qte'] is None:
            validated_data['qte'] = 1
        return super().create(validated_data)


       
class CreateArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = article
        fields = [
            'id', 'produit', 'nature', 'fournisseur', 'image',
            'code_article', 'designation', 'date_achat', 'numero_comptable',
            'couleur', 'poids', 'volume', 'langueur', 'hauteur', 'largeur',
            'date_expiration', 'date_peremption', 'date_reception',
            'prix_achat', 'attachement1', 'attachement2', 'marque', 
            'N_facture', 'attachement3', 'qte',
        ]

    error_messages = {
        'produit': {
            'blank': 'Le champ produit ne peut pas être vide.',
            'required': 'Veuillez spécifier un produit.',
        },
        'qte': {
            'blank': 'Le champ quantité ne peut pas être vide.',
            'invalid': 'La quantité doit être un nombre valide.',
        },
        'N_facture': {
            'blank': 'Le champ numéro de facture ne peut pas être vide.',
        },
        'code_article': {
            'blank': 'Le champ code article ne peut pas être vide.',
        },
        'designation': {
            'blank': 'Le champ désignation ne peut pas être vide.',
        },
        'date_expiration': {
            'invalid': 'Le format de la date d\'expiration est incorrect. Veuillez utiliser le format YYYY-MM-DD.',
        },
    }

    def validate(self, attrs):
        # Validation des relations avec les libellés/noms
        attrs['produit'] = self.validate_relation(attrs.get('produit'), produit, 'libelle', "produit")
        attrs['marque'] = self.validate_relation(attrs.get('marque'), marque, 'nom', "marque")
        attrs['fournisseur'] = self.validate_relation(attrs.get('fournisseur'), fournisseur, 'nom', "fournisseur")
        attrs['nature'] = self.validate_relation(attrs.get('nature'), nature, 'libelle', "nature")

        # Validation des champs de date
        for date_field in ['date_peremption', 'date_expiration', 'date_reception', 'date_achat']:
            if date_field in attrs:
                attrs[date_field] = self.validate_date(attrs[date_field], date_field)

        return attrs

    def validate_relation(self, value, model, field_name, field_label):

        if value:
            try:
                return model.objects.get(**{field_name: value})
            except model.DoesNotExist:
                raise serializers.ValidationError({field_label: f"{field_label.capitalize()} '{value}' non trouvé."})
        return value

    def validate_date(self, date_value, field_label):
        """Valide le format de la date."""
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError({field_label: f"Date invalide pour '{date_value}'."})
        return date_value

    def create(self, validated_data):
        return article.objects.create(**validated_data)    


class PersonneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personne
        fields = '__all__'

class UpdateItemArticleSerializer(serializers.ModelSerializer):
    produit = serializers.IntegerField(write_only=True, required=False)
    nature = serializers.IntegerField(write_only=True, required=False, allow_null=True)  
    fournisseur = serializers.IntegerField(write_only=True, required=False)
    marque = serializers.IntegerField(write_only=True, required=False, allow_null=True)  
    categorie = serializers.IntegerField(write_only=True, required=False)  
    N_facture = serializers.CharField(required=False)  # Assurez-vous qu'il n'est pas read_only

    class Meta:
        model = article
        fields = ['produit', 'nature', 'fournisseur', 'categorie', 'marque', 'N_facture']

    def update(self, instance, validated_data):
        print("Données validées :", validated_data)  # Debug pour voir les données validées

        instance.produit_id = validated_data.get('produit', instance.produit_id)
        instance.nature_id = validated_data.get('nature', instance.nature_id)  
        instance.fournisseur_id = validated_data.get('fournisseur', instance.fournisseur_id)
        instance.marque_id = validated_data.get('marque', instance.marque_id)

        # Vérification et mise à jour de N_facture
        if 'N_facture' in validated_data:
            print(f"Mise à jour de N_facture : {instance.N_facture} → {validated_data['N_facture']}")
            instance.N_facture = validated_data['N_facture']

        instance.save()

        # Vérifier si la base de données est bien mise à jour
        instance.refresh_from_db()
        print(f"Valeur en base après mise à jour : {instance.N_facture}")

        return instance
    


class ItemsSerializer(serializers.ModelSerializer):
    """Aggregate representation of an `item` including nested article and context fields."""
    emplacement = serializers.StringRelatedField(source='emplacement.nom', read_only=True)
    zone = serializers.StringRelatedField(source='emplacement.zone.nom', read_only=True)
    departement = serializers.StringRelatedField(source='departement.nom', read_only=True)
    affectation_personne_full_name = serializers.SerializerMethodField()
    article = ArticleSerializeres()  # Assurez-vous que cela fonctionne
    tag = serializers.StringRelatedField(source='tag.reference', read_only=True)
    valeur_residuelle = serializers.SerializerMethodField()
    produit_categorie = serializers.SerializerMethodField()
    commentaire = serializers.SerializerMethodField()  # Changez ce champ
    fournis = serializers.StringRelatedField(source='article.fournisseur.nom', read_only=True)
    fournisseur = serializers.StringRelatedField(source='article.fournisseur.nom', read_only=True)

    class Meta:
        model = item
        fields = [
            'id',
            'date_affectation',
            'emplacement',
            'zone',
            'departement',
            'article',
            'valeur_residuelle',
            'tag',
            'affectation_personne_full_name',
            'numero_serie',
            'fournis',
            'fournisseur',
            'archive',
            'created_at',
            'updated_at',
            'statut',
            'produit_categorie',  
            'commentaire'
        ]

    def get_affectation_personne_full_name(self, obj):
        return f"{obj.affectation_personne.nom} {obj.affectation_personne.prenom}" if obj.affectation_personne else None

    def get_produit_categorie(self, obj):
        if obj.article and obj.article.produit:
            return obj.article.produit.categorie.libelle
        return None
    
    def get_zone(self,obj):
        return obj.emplacement.zone

    def get_valeur_residuelle(self, obj):
        return obj.calculate_residual_value()

    def get_commentaire(self, obj):
        # Récupérer le dernier commentaire lié à cet item
        last_archive_item = obj.archive_items.last()  # Récupérer le dernier ArchiveItem
        return last_archive_item.commentaire if last_archive_item else None
    def get_fournisseur(self, obj):
        return obj.article.fournisseur.nom if obj.article and obj.article.fournisseur else ""



class DepartementSerializer(serializers.ModelSerializer):
    class Meta:
        model = departement
        fields = '__all__'


class TypeTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = type_tag
        fields = '__all__'

class FournisseurSerializer(serializers.ModelSerializer):
    class Meta:
        model = fournisseur
        fields = '__all__'

class NatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = nature
        fields = '__all__'
        
        
        
class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = categorie
        fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = tag
        fields = '__all__'


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = zone
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = location
        fields = '__all__'
        

class PersonneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personne
        fields = '__all__'


class EmplacementSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    tag = serializers.SerializerMethodField()
    class Meta:
        model = emplacement
        fields = '__all__'
    def get_location(self, obj):
        return obj.zone.location.nom if obj.zone.location.nom else None
    
    def get_tag(self, obj):
        # Access the tag reference directly through the tag field
        return obj.tag.reference if obj.tag else None


class InventaireEmplacementSerializer(serializers.ModelSerializer):
    class Meta:
        
        model = inventaire_emplacement
        fields = '__all__'

class InventairesEmplacementSerializer(serializers.ModelSerializer):
    emplacement_nom = serializers.CharField(source='emplacement.nom')
    inventaire_nom = serializers.CharField(source='inventaire.nom')
    inventaire_id = serializers.CharField(source='inventaire.id')
    date_creation = serializers.CharField(source='inventaire.date_creation')
    emplacement_id = serializers.CharField(source='emplacement.id')

    class Meta:
        model = inventaire_emplacement
        fields = ('id','statut','emplacement_id',"inventaire_id" ,'date_creation', 'emplacement_nom', 'inventaire_nom')


class InventaireSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    emplacement = serializers.SerializerMethodField()
    
    class Meta:
        model = inventaire
        fields = ('id', 'reference', 'nom', 'statut','emplacement', 'user', 'created_at')
    
    def get_user(self, obj):
        # Retourne le nom complet si disponible, sinon username
        try:
            if getattr(obj.user, 'nom', None) or getattr(obj.user, 'prenom', None):
                nom = getattr(obj.user, 'nom', '') or ''
                prenom = getattr(obj.user, 'prenom', '') or ''
                full_name = f"{nom} {prenom}".strip()
                return full_name if full_name else getattr(obj.user, 'username', None)
            return getattr(obj.user, 'username', None)
        except Exception:
            return None

    def get_emplacement(self, obj):
        """Retourne le nom du premier emplacement lié (s'il existe) de manière robuste."""
        # 1) Via prefetch (relation reverse standard _set)
        try:
            rel_qs = getattr(obj, 'inventaire_emplacement_set', None)
            if rel_qs is not None:
                first_link = rel_qs.all().select_related('emplacement').order_by('id').first()
                if first_link and getattr(first_link, 'emplacement', None):
                    return first_link.emplacement.nom
        except Exception:
            pass

        # 2) Fallback: requête directe optimisée
        try:
            from .models import inventaire_emplacement  # import local
            first_link = (
                inventaire_emplacement.objects
                .filter(inventaire_id=obj.id)
                .select_related('emplacement')
                .order_by('id')
                .values_list('emplacement__nom', flat=True)
                .first()
            )
            if first_link:
                return first_link
        except Exception:
            pass

        return None


class InventaireLocationSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'API InventaireLocationListsAPIView
    Champs: id, reference, libelle (nom), statut, location, user, date_creation, created_at
    """
    user = serializers.SerializerMethodField()
    libelle = serializers.CharField(source='nom', read_only=True)
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = inventaire
        fields = ('id', 'reference', 'libelle', 'statut', 'location', 'user', 'date_creation', 'created_at')
    
    def get_user(self, obj):
        """Retourne le nom complet de l'utilisateur"""
        try:
            if hasattr(obj.user, 'nom') and hasattr(obj.user, 'prenom'):
                nom = obj.user.nom or ''
                prenom = obj.user.prenom or ''
                full_name = f"{nom} {prenom}".strip()
                return full_name if full_name else obj.user.username
            return obj.user.username
        except Exception:
            return None
    
    def get_location(self, obj):
        """Retourne le nom de la première location liée via emplacement->zone->location"""
        try:
            # Utiliser le prefetch si disponible
            inv_emp_qs = getattr(obj, 'inventaire_emplacement_set', None)
            if inv_emp_qs is not None:
                first_link = inv_emp_qs.all().order_by('id').first()
                if first_link and hasattr(first_link, 'emplacement'):
                    if hasattr(first_link.emplacement, 'zone') and first_link.emplacement.zone:
                        if hasattr(first_link.emplacement.zone, 'location') and first_link.emplacement.zone.location:
                            return first_link.emplacement.zone.location.nom
            
            # Fallback: requête directe optimisée
            from .models import inventaire_emplacement
            location_nom = (
                inventaire_emplacement.objects
                .filter(inventaire_id=obj.id)
                .select_related('emplacement__zone__location')
                .order_by('id')
                .values_list('emplacement__zone__location__nom', flat=True)
                .first()
            )
            return location_nom if location_nom else None
        except Exception:
            return None


class InventaireZoneSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'API InventaireZoneListsAPIView
    Champs: id, reference, libelle (nom), statut, zone, user, date_creation, created_at
    """
    user = serializers.SerializerMethodField()
    libelle = serializers.CharField(source='nom', read_only=True)
    zone = serializers.SerializerMethodField()
    
    class Meta:
        model = inventaire
        fields = ('id', 'reference', 'libelle', 'statut', 'zone', 'user', 'date_creation', 'created_at')
    
    def get_user(self, obj):
        """Retourne le nom complet de l'utilisateur"""
        try:
            if hasattr(obj.user, 'nom') and hasattr(obj.user, 'prenom'):
                nom = obj.user.nom or ''
                prenom = obj.user.prenom or ''
                full_name = f"{nom} {prenom}".strip()
                return full_name if full_name else obj.user.username
            return obj.user.username
        except Exception:
            return None
    
    def get_zone(self, obj):
        """Retourne le nom de la première zone liée via emplacement->zone"""
        try:
            # Utiliser le prefetch si disponible
            inv_emp_qs = getattr(obj, 'inventaire_emplacement_set', None)
            if inv_emp_qs is not None:
                first_link = inv_emp_qs.all().order_by('id').first()
                if first_link and hasattr(first_link, 'emplacement'):
                    if hasattr(first_link.emplacement, 'zone') and first_link.emplacement.zone:
                        return first_link.emplacement.zone.nom
            
            # Fallback: requête directe optimisée
            from .models import inventaire_emplacement
            zone_nom = (
                inventaire_emplacement.objects
                .filter(inventaire_id=obj.id)
                .select_related('emplacement__zone')
                .order_by('id')
                .values_list('emplacement__zone__nom', flat=True)
                .first()
            )
            return zone_nom if zone_nom else None
        except Exception:
            return None


class InventaireDepartementSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'API InventaireDepartementListAPIView
    Champs: id, reference, libelle (nom), statut, departement, user, date_creation, created_at
    """
    user = serializers.SerializerMethodField()
    libelle = serializers.CharField(source='nom', read_only=True)
    departement = serializers.CharField(source='departement.nom', read_only=True)
    
    class Meta:
        model = inventaire
        fields = ('id', 'reference', 'libelle', 'statut', 'departement', 'user', 'date_creation', 'created_at')
    
    def get_user(self, obj):
        """Retourne le nom complet de l'utilisateur"""
        try:
            if hasattr(obj.user, 'nom') and hasattr(obj.user, 'prenom'):
                nom = obj.user.nom or ''
                prenom = obj.user.prenom or ''
                full_name = f"{nom} {prenom}".strip()
                return full_name if full_name else obj.user.username
            return obj.user.username
        except Exception:
            return None


class InventaireEmplacementDetailSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'API InventaireEmplacementsDetailAPIView
    Champs: id, emplacement, operateur (nom complet), statut, etat (start_at)
    """
    emplacement = serializers.CharField(source='emplacement.nom', read_only=True)
    operateur = serializers.SerializerMethodField()
    etat = serializers.BooleanField(source='start_at', read_only=True)
    
    class Meta:
        model = inventaire_emplacement
        fields = ('id', 'emplacement', 'operateur', 'statut', 'etat', 'created_at')
    
    def get_operateur(self, obj):
        """Retourne le nom complet de l'opérateur (affceted_at)"""
        try:
            if obj.affceted_at:
                nom = obj.affceted_at.nom or ''
                prenom = obj.affceted_at.prenom or ''
                return f"{nom} {prenom}".strip()
            return ""
        except Exception:
            return ""


class InventaireEmplacementSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple pour InventaireEmplacementDetailAPIView
    Retourne: id, emplacement_id, emplacement_nom, statut
    """
    emplacement_id = serializers.IntegerField(source='emplacement.id', read_only=True)
    emplacement_nom = serializers.CharField(source='emplacement.nom', read_only=True)
    
    class Meta:
        model = inventaire_emplacement
        fields = ('id', 'emplacement_id', 'emplacement_nom', 'statut', 'created_at')


class DetailInventaireSerializer(serializers.ModelSerializer):
    inventaire = serializers.PrimaryKeyRelatedField(queryset=inventaire.objects.all())
    item = serializers.PrimaryKeyRelatedField(queryset=item.objects.all())
    
    class Meta:
        model = detail_inventaire
        fields = ['inventaire', 'item', 'etat']

    def create(self, validated_data):
        return detail_inventaire.objects.create(**validated_data)
    
class CreatDetailInventaireSerializer(serializers.ModelSerializer):

    class Meta:
        model = detail_inventaire
        fields = ['inventaire_emplacement', 'item', 'etat']




from datetime import datetime
class OperationItemsSerializer(serializers.ModelSerializer):
    """Lightweight view of item operation attachments and references."""
    item_designation = serializers.SerializerMethodField()  # Pour récupérer la désignation de l'article
    operation_reference = serializers.SerializerMethodField()
    tag = serializers.SerializerMethodField()# Pour récupérer la référence de l'opération

    class Meta:
        model = operation_article  # Assurez-vous que 'operation_article' est correctement importé
        fields = ['id', 'operation_reference', 'item_designation', 'prix', 'date_operation', 'commentaire', 'attachement', 'tag', 'created_at', 'updated_at']

    def get_item_designation(self, obj):
        if obj.item and obj.item.article:  # Vérifie que l'item et l'article existent
            return obj.item.article.designation  # Récupère la désignation de l'article lié
        return None  # Retourne None si l'article n'existe pas

    def get_tag(self, obj):
        if obj.item and obj.item.tag.reference:  # Vérifie que l'item et l'article existent
            return obj.item.tag.reference  # Récupère la désignation de l'article lié
        return None  #
    
    def get_operation_reference(self, obj):
        if obj.operation:  # Vérifie si l'opération existe
            return obj.operation.reference  # Récupère la référence de l'opération liée
        return None  # Retourne None si l'opération est vide

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.attachement:  # Vérifie si l'attachement existe
            file_url = instance.attachement.url  # Obtient l'URL de l'attachement
            file_type = instance.attachement.name.split('.')[-1].lower()  # Détermine le type de fichier

            # Vérifie si l'attachement est une image
            if file_type in ['jpg', 'jpeg', 'png', 'gif']:  # Types d'images
                representation['attachement_url'] = urljoin(settings.SITE_URL, file_url)  # URL de l'image
            else:
                representation['attachement_url'] = urljoin(settings.SITE_URL, file_url)  # URL du fichier (PDF, DOCX, etc.)
                representation['attachement_file'] = urljoin(settings.SITE_URL, file_url)  # URL pour le téléchargement
        else:
            representation['attachement_url'] = 'auccun fichier'  # URL du fichier (PDF, DOCX, etc.)
            representation['attachement_file'] =  'auccun fichier'

        return representation


class DetailInventairesSerializer(serializers.ModelSerializer):
    """Serializer for inventory lines enriched with item/emplacement labels."""
    # inventaire = serializers.SerializerMethodField()
    item = serializers.SerializerMethodField()
    emplacement = serializers.SerializerMethodField()  # Nouveau champ pour l'emplacement
    item_id = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()
    emplacement_origine = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    start_at = serializers.SerializerMethodField()  # Champ start_at de inventaire_emplacement

    class Meta:
        model = detail_inventaire
        fields = ['item_id', 'reference', 'emplacement_origine', 'item', 'emplacement', 'etat', 'start_at', 'created_at']

    def get_emplacement_origine(self,obj):
        return obj.item.emplacement.nom
    def get_item(self, obj):
        return  obj.item.article.designation
    def get_item_id(self,obj):
        return obj.item.id
    def get_reference(self,obj):
        return obj.item.article.code_article

    def get_emplacement(self, obj):
        # Retourner le nom de l'emplacement de l'item
        return obj.inventaire_emplacement.emplacement.nom  # Ajuste en fonction des attributs de ton modèle

    def get_start_at(self, obj):
        # Retourner le champ start_at de inventaire_emplacement
        if obj.inventaire_emplacement:
            return obj.inventaire_emplacement.start_at
        return False

    def get_created_at(self, obj):
        # Format du champ created_at en DD:MM:YYYY:HH:MM:SS
        return obj.created_at.strftime('%d/%m/%Y-%H:%M:%S')








class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = operation
        fields = '__all__'
        
import os
from django.core.exceptions import ValidationError

class OperationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = operation_article
        fields = ['item', 'operation', 'prix', 'date_operation', 'attachement', 'commentaire']

    def validate_attachement(self, value):
        # Check if there's a file attached
        if value:
            # Allowed file extensions
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx']
            ext = os.path.splitext(value.name)[1][1:].lower()  # Get file extension

            if ext not in allowed_extensions:
                raise ValidationError(f'Unsupported file extension. Allowed extensions are: {", ".join(allowed_extensions)}')
        
        return value



class TagHistorySerializer(serializers.ModelSerializer):
    old_tag_reference = serializers.CharField(source='old_tag.reference', read_only=True)
    new_tag_reference = serializers.CharField(source='new_tag.reference', read_only=True)
    item_designation = serializers.CharField(source='item.article.designation', read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = TagHistory
        fields = ['id', 'item_designation', 'old_tag_reference', 'new_tag_reference', 'user_full_name']

    def get_user_full_name(self, obj):
        # Assure-toi que changed_by est bien un champ dans TagHistory et qu'il fait référence à un UserWeb
        if obj.changed_by:
            return f"{obj.changed_by.nom} {obj.changed_by.prenom}"
        return "Unknown User"


class TagAffectationSerializer(serializers.Serializer):
    emplacementId = serializers.IntegerField()
    tag_reference = serializers.CharField(max_length=250)

    def validate(self, data):
        # Vérifier si l'emplacement existe
        try:
            emplacement_instance = emplacement.objects.get(id=data['emplacementId'])
        except emplacement.DoesNotExist:
            raise serializers.ValidationError("L'emplacement avec cet ID n'existe pas.")
        
        # Vérifier si le tag existe
        try:
            tag_instance = tagEmplacement.objects.get(reference=data['tag_reference'])
        except tagEmplacement.DoesNotExist:
            raise serializers.ValidationError("Le tag avec cette référence n'existe pas.")
        
        # Vérifier si le tag est déjà affecté
        if tag_instance.affecter:
            raise serializers.ValidationError("Ce tag est déjà affecté à un autre emplacement.")
        
        # Ajouter les instances dans les données validées
        data['emplacement_instance'] = emplacement_instance
        data['tag_instance'] = tag_instance
        return data
    


class CategorieItemCountSerializer(serializers.ModelSerializer):
    total_items = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source='libelle', read_only=True)

    class Meta:
        model = categorie
        fields = ['name', 'total_items']  # Inclut uniquement le libelle et le total_items


class TypeTagCountSerializer(serializers.ModelSerializer):
    total_items = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source='nom', read_only=True)

    class Meta:
        model = type_tag
        fields = ['name', 'total_items']  
        
class ItemCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
class ArticleCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
class tagsCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    
class ArchivedItemsCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    
class AmortizationCountSerializer(serializers.Serializer):
    total_amortized = serializers.IntegerField()
    total_non_amortized = serializers.IntegerField()
    

class FinancialValueSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_value(self, value):
        # Check if value is not None and is a valid decimal
        if value is None or not isinstance(value, (int, float, Decimal)):
            raise serializers.ValidationError("Total residual value must be a valid number.")
        return value
class LocationWithEmplacementCountSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(read_only=True)

    class Meta:
        model = location
        fields = ['nom', 'value']
        
class DepartementCountSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = departement
        fields = ['nom',  'value']

    def get_value(self, obj):
        return obj.item_set.count()
    
class PersonneItemSummarySerializer(serializers.ModelSerializer):
    # Champ pour le nom complet
    nom_complet = serializers.SerializerMethodField()
    valeur_residuelle_totale = serializers.SerializerMethodField()
    quantite_items = serializers.IntegerField(source='item_set.count', read_only=True)

    class Meta:
        model = Personne
        fields = ['nom_complet', 'quantite_items', 'valeur_residuelle_totale']

    def get_nom_complet(self, personne):
        return f"{personne.nom} {personne.prenom}"

    def get_valeur_residuelle_totale(self, personne):
        items = item.objects.filter(affectation_personne=personne)
        return sum(item.calculate_residual_value() for item in items)
    
class TransferHistoriqueSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple pour l'historique des transferts
    Retourne seulement les IDs (pour édition/création)
    """
    class Meta:
        model = TransferHistorique
        fields = '__all__'


class TransferHistoriqueSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour l'historique des transferts
    Retourne les noms ET les IDs pour meilleure lisibilité
    """
    # Informations de l'item
    item_reference = serializers.CharField(source='item_transfer.reference_auto', read_only=True)
    item_designation = serializers.CharField(source='item_transfer.article.designation', read_only=True)
    
    # Emplacements (noms)
    old_emplacement_nom = serializers.CharField(source='old_emplacement.nom', read_only=True)
    new_emplacement_nom = serializers.CharField(source='new_emplacement.nom', read_only=True)
    
    # Départements (noms)
    old_departement_nom = serializers.CharField(source='old_departement.nom', read_only=True)
    new_departement_nom = serializers.CharField(source='new_departement.nom', read_only=True)
    
    # Personnes (noms complets)
    old_personne_nom = serializers.SerializerMethodField()
    new_personne_nom = serializers.SerializerMethodField()
    
        
    class Meta:
        model = TransferHistorique
        fields = [
            # Identifiants
            'id',
            'created_at',
            'updated_at',
            
            # Item
            'item_reference',
            'item_designation',
            
            # Emplacements (IDs + noms)
            'old_emplacement_nom',
            'new_emplacement_nom',
            
            # Départements (IDs + noms)
            'old_departement_nom',
            'new_departement_nom',
            
            # Personnes (IDs + noms)
            'old_personne_nom',
            'new_personne_nom'
        ]
    
    def get_old_personne_nom(self, obj):
        """Retourne le nom complet de l'ancienne personne"""
        if obj.old_personne:
            return f"{obj.old_personne.nom} {obj.old_personne.prenom}"
        return None
    
    def get_new_personne_nom(self, obj):
        """Retourne le nom complet de la nouvelle personne"""
        if obj.new_personne:
            return f"{obj.new_personne.nom} {obj.new_personne.prenom}"
        return None


class ItemNewSerializer(serializers.ModelSerializer):
    # Nested related fields
    article = ArticleSerializer(read_only=True)
    emplacement = EmplacementSerializer(read_only=True)
    departement = DepartementSerializer(read_only=True)
    affectation_personne = PersonneSerializer(read_only=True)

    class Meta:
        model = item
        fields = ['reference_auto', 'statut', 'archive', 'numero_serie', 'date_affectation', 
                  'date_archive', 'emplacement', 'departement', 'affectation_personne', 
                  'article', 'created_at', 'updated_at']


class ArchiveItemSerializer(serializers.ModelSerializer):
    """
    Serializer pour représenter une ligne d'archivage d'item (ArchiveItem)
    avec quelques informations utiles sur l'item source.
    """

    item_id = serializers.IntegerField(source="item_archive.id", read_only=True)
    item_reference = serializers.CharField(
        source="item_archive.reference_auto", read_only=True
    )
    item_designation = serializers.CharField(
        source="item_archive.article.designation", read_only=True
    )
    item_numero_serie = serializers.CharField(
        source="item_archive.numero_serie", read_only=True
    )

    class Meta:
        model = ArchiveItem
        fields = [
            "id",
            "item_id",
            "item_reference",
            "item_designation",
            "item_numero_serie",
            "commentaire",
            "created_at",
            "updated_at",
        ]


class ArchiveItemExcelImportSerializer(serializers.Serializer):
    """
    Serializer d'entrée pour l'API d'import Excel des archivages d'items.

    Attendu :
    - file : fichier Excel (.xlsx) avec au moins une colonne 'id' (ID de l'item)
      et optionnellement une colonne 'commentaire'.
    - skip_errors : si False, la première erreur stoppe l'import.
    """

    file = serializers.FileField()
    skip_errors = serializers.BooleanField(default=True)


class ArchiveItemBatchSerializer(serializers.Serializer):
    """
    Serializer d'entrée pour l'API batch d'archivage.

    Attendu :
    - items_id : liste d'IDs d'items
    """

    items_id = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
