"""Masterdata domain models: users, taxonomy, locations, assets (articles/items), tags and inventory.

This module centralizes business objects and core rules such as reference generation
and residual value calculations. Keep models cohesive and document behaviors.
"""
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.models import Group, Permission
from simple_history.models import HistoricalRecords
from datetime import datetime

# === Comptes et Utilisateurs ===


class Compte(models.Model):
    """Account/tenant to partition data and settings across the platform."""
    libelle = models.CharField(max_length=255)
    code_compte = models.CharField(max_length=255,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.libelle  

class UserWebManager(BaseUserManager):
    """Custom manager used for creating standard users and superusers."""
    def create_user(self, email, role, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, role, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, role, password, **extra_fields)

class UserWeb(AbstractBaseUser, PermissionsMixin, models.Model):  
    """Primary user model for web/mobile with role-based access and groups."""
    ROLES = (
        ('Administrateur', 'Administrateur'),
        ('user', 'User'),
    )
    type = (
        ('web', 'web'),
        ('mobile', 'mobile'),
    )
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length = 255)
    prenom = models.CharField(max_length = 255)
    role = models.CharField(max_length=100, choices=ROLES)
    type = models.CharField(max_length=100, choices=type,default="web")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False,verbose_name='Administrateur',)
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE,blank=True,null=True)
    objects = UserWebManager()
    history = HistoricalRecords()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['role']
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        related_name='user_web_groups' # Nouveau nom de relation
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        related_name='user_web_permissions' # Nouveau nom de relation
    )
    def __str__(self):
        return f"{self.prenom} {self.nom}"


    class Meta:
        verbose_name = 'Utilisateur'






class SuperUserProxy(UserWeb):
    """Proxy model used to isolate superusers in the admin interface."""
    class Meta:
        proxy = True
        verbose_name = "Super Utilisateur"
        verbose_name_plural = "Super Utilisateurs"


import re

class Personne(models.Model):
    """Physical person to which items can be assigned (affectation)."""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    prenom = models.CharField(max_length=100)
    nom = models.CharField(max_length=100)
    reference = models.CharField(max_length = 255,unique=True)
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
    
    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                Personne.objects.filter(reference__startswith="PRSN-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'PRSN-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"PRSN-{next_number:06d}"

        super().save(*args, **kwargs)



class categorie(models.Model):
    """Product family category (e.g., IT, Vehicles, Furniture)."""
    libelle = models.CharField(max_length = 255,unique=True)
    reference = models.CharField(max_length = 255,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.libelle
    
    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                categorie.objects.filter(reference__startswith="CAT-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'CAT-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"CAT-{next_number:06d}"

        super().save(*args, **kwargs)

    

class produit(models.Model):
    """Product family (template) with amortization duration and management mode."""
    type = [
        ('en masse', 'en masse'),
        ('individuellement', 'individuellement'),
        
    ]
    libelle = models.CharField(max_length = 255,unique=True)
    code_produit = models.CharField(max_length = 255, verbose_name="Reference",unique=True)
    categorie = models.ForeignKey(categorie, on_delete=models.CASCADE)
    duree_amourtissement = models.IntegerField(default=3, verbose_name="Durée d'amortissement")
    statut = models.CharField(choices=type ,max_length = 250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    class Meta:
        verbose_name = " Famille"
    def __str__(self):
        return self.libelle
    
    
    def save(self, *args, **kwargs):
        if not self.code_produit:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_code_produit = (
                produit.objects.filter(code_produit__startswith="PRD-")
                .order_by('-code_produit')
                .values_list('code_produit', flat=True)
                .first()
            )
            if last_code_produit:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'PRD-(\d+)', last_code_produit)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.code_produit = f"PRD-{next_number:06d}"

        super().save(*args, **kwargs)



class nature(models.Model):
    """Domain-specific nature of an article (custom taxonomy)."""
    libelle = models.CharField(max_length = 255,unique=True)
    reference = models.CharField(max_length = 255,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.libelle
    
    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                nature.objects.filter(reference__startswith="NTR-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'NTR-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"NTR-{next_number:06d}"

        super().save(*args, **kwargs)



class fournisseur(models.Model):
    """Supplier providing articles/assets."""
    nom = models.CharField(max_length=250)
    reference = models.CharField(max_length=250, unique=True)  
    ice = models.CharField(max_length=250, default="Null")
    tel = models.CharField(max_length=50, default="Null")
    adresse = models.CharField(max_length=250,default="Null")
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                fournisseur.objects.filter(reference__startswith="FRN-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'FRN-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"FRN-{next_number:06d}"

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.nom}"

class operation(models.Model):
    """Operation reference to attach files/comments on items."""
    reference = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.reference


class departement(models.Model):
    """Organizational department owning or using items."""
    nom = models.CharField(max_length = 255,unique=True)
    reference = models.CharField(max_length = 255,unique=True)
    compte = models.ForeignKey(Compte,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    history = HistoricalRecords()
    def __str__(self):
        return self.nom  
    
    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                departement.objects.filter(reference__startswith="DPR-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'DPR-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"DPR-{next_number:06d}"

        super().save(*args, **kwargs)
 


# === Localisation (Sites, Zones, Emplacements) ===

class location(models.Model):
    """Physical site/location (e.g., building/campus)."""
    nom = models.CharField(max_length = 250,unique=True)
    reference = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    compte = models.ForeignKey(Compte,on_delete=models.CASCADE)
    history = HistoricalRecords()
    class Meta:
        verbose_name = " Local"
    def __str__(self):
        return self.nom
    
    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                location.objects.filter(reference__startswith="LOC-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'LOC-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"LOC-{next_number:06d}"

        super().save(*args, **kwargs)

    

class zone(models.Model):
    """Area within a location (e.g., floor/wing)."""
    nom = models.CharField(max_length = 250,unique=True)
    location = models.ForeignKey(location, on_delete=models.CASCADE)
    reference = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom
    
    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                zone.objects.filter(reference__startswith="ZONE-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'ZONE-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"ZONE-{next_number:06d}"

        super().save(*args, **kwargs)


class emplacement(models.Model):
    """Precise place to store or assign items (e.g., room/shelf)."""
    nom = models.CharField(max_length = 250,unique=True)
    zone = models.ForeignKey(zone, on_delete=models.CASCADE)
    reference = models.CharField(max_length = 250,unique=True)
    tag = models.OneToOneField('tagEmplacement', on_delete=models.CASCADE,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom
    
    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                emplacement.objects.filter(reference__startswith="EMP-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'EMP-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"EMP-{next_number:06d}"

        super().save(*args, **kwargs)



# class EmplacementTag(emplacement):
#     class Meta:
#         proxy = True
#         verbose_name = "Affectation du Tag emplacement"


# === Référentiels divers ===

class marque(models.Model):
    """Brand of article or equipment."""
    nom = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom

class type_tag(models.Model):
    """Type of tags used for items or locations."""
    nom = models.CharField(max_length = 250,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom



class Fichier(models.Model):
    """Metadata for imported files (size, number of rows)."""
    nom = models.CharField(max_length=255,unique=True)
    taille = models.PositiveIntegerField()  # taille en octets, par exemple
    nombre_lignes = models.PositiveIntegerField()
    
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.nom} - {self.taille} octets - {self.nombre_lignes} lignes"


class article(models.Model):
    """Purchased article (acquisition). Can generate one or more concrete items."""
    
    code_article = models.CharField(max_length = 250,unique=False,blank=True,null=True)
    designation = models.CharField(max_length = 250,unique=False)
    date_achat = models.DateField()
    numero_comptable = models.CharField(max_length = 250,blank=True,null=True)
    image = models.ImageField(upload_to='_images_articles/',blank=True,null=True)
    couleur = models.CharField(max_length = 100,blank=True,null=True)
    poids = models.FloatField(blank=True,null=True)
    volume = models.FloatField(blank=True,null=True)
    langueur = models.FloatField(blank=True,null=True)
    hauteur= models.FloatField(blank=True,null=True)
    largeur = models.FloatField(blank=True,null=True)
    date_expiration = models.DateField(blank=True,null=True)
    date_peremption = models.DateField(blank=True,null=True)
    date_reception = models.DateTimeField(auto_now_add=True)
    prix_achat = models.FloatField(default=0)
    attachement1 = models.FileField(blank=True,null=True,upload_to='_fichier_article/')
    attachement2 = models.FileField(blank=True,null=True,upload_to='_fichier_article/')
    attachement3 = models.FileField(blank=True,null=True,upload_to='_fichier_article/')
    qte = models.IntegerField(default=1,null=True)
    qte_recue = models.IntegerField(blank=True,null=True)
    N_facture = models.CharField(max_length=255)
    valider = models.BooleanField(default = True)
    via_erp = models.BooleanField(default = False,blank=True,null=True)
    compte = models.ForeignKey(Compte, on_delete=models.CASCADE)
    produit = models.ForeignKey(produit, on_delete=models.CASCADE)
    marque = models.ForeignKey(marque, on_delete=models.CASCADE,blank=True,null=True)
    fournisseur = models.ForeignKey(fournisseur, on_delete=models.CASCADE,blank=True,null=True)
    nature = models.ForeignKey(nature, on_delete=models.CASCADE,blank=True,null=True)    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fichier = models.ForeignKey(Fichier, on_delete=models.CASCADE,null=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.designation
    
    def save(self, *args, **kwargs):
        if self.qte_recue is None:
            self.qte_recue = self.qte
        if not self.code_article:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                article.objects.filter(code_article__startswith="ARTL-")
                .order_by('-code_article')
                .values_list('code_article', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'ARTL-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.code_article = f"ARTL-{next_number:06d}"

        super().save(*args, **kwargs)
    





class item(models.Model):
    """Concrete, trackable unit (asset) created from an `article` and located/assigned."""
    statut = [
        ('affecter', 'affecter'),
        ('non affecter', 'non affecter'), 
        
    ]
    reference_auto = models.CharField(max_length=255,blank=True,null=True)
    date_affectation = models.DateField(blank=True,null=True,auto_now_add=True)
    statut = models.CharField(choices=statut ,max_length = 250,default='non affecter')
    archive = models.BooleanField(default = False)
    date_archive = models.DateField(blank=True, null=True)
    affectation_personne=models.ForeignKey(Personne,on_delete=models.CASCADE,blank=True, null=True)
    numero_serie = models.CharField(max_length=250,blank=True,null=True,unique=False)
    emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE)
    departement = models.ForeignKey(departement, on_delete=models.CASCADE,unique=False,default=1)
    article = models.ForeignKey(article, on_delete=models.CASCADE)  
    tag = models.OneToOneField('tag', on_delete=models.CASCADE,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.statut
    
    def save(self, *args, **kwargs):
        if not self.reference_auto:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                item.objects.filter(reference_auto__startswith="ITEM-")
                .order_by('-reference_auto')
                .values_list('reference_auto', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'ITEM-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference_auto = f"ITEM-{next_number:06d}"

        super().save(*args, **kwargs)

    def calculate_residual_value(self, year=None):
        """Compute linear residual value of this item for a given year.

        The calculation uses the amortization duration defined on the product family
        and the item's purchase price. If `year` is omitted, the current year is used.
        Returns None if data is incomplete.
        """
        if not self.article:
            return None

        duree_amortissement = self.article.produit.duree_amourtissement
        prix_achat = self.article.prix_achat

        if duree_amortissement is None or prix_achat is None:
            return None

        taux_amortissement = (100 / duree_amortissement) / 100
        montant_annuel = taux_amortissement * prix_achat

        # Si aucune année n'est spécifiée, utiliser l'année actuelle
        current_year = year if year is not None else datetime.now().year
        purchase_year = self.article.date_achat.year
        annee = current_year - purchase_year

        if annee > duree_amortissement:
            valeur_residuelle = prix_achat - (montant_annuel * duree_amortissement)
        else:
            valeur_residuelle = prix_achat - (montant_annuel * annee)

        return max(valeur_residuelle, 0)

class TransferHistorique(models.Model):
    """History of item transfers between locations, departments or people."""
    item_transfer = models.ForeignKey(item, on_delete=models.CASCADE)
    new_emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE, blank=True, null=True, related_name='new_emplacement_transfers')
    old_emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE, blank=True, null=True, related_name='old_emplacement_transfers')
    new_personne = models.ForeignKey(Personne, on_delete=models.CASCADE, blank=True, null=True, related_name='new_personne_transfers')
    old_personne = models.ForeignKey(Personne, on_delete=models.CASCADE, blank=True, null=True, related_name='old_personne_transfers')
    new_departement = models.ForeignKey(departement, on_delete=models.CASCADE, blank=True, null=True, related_name='new_departement_transfers')
    old_departement = models.ForeignKey(departement, on_delete=models.CASCADE, blank=True, null=True, related_name='old_departement_transfers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

class tag(models.Model):
    """RFID/Barcode tag assigned to items."""
    statut = [
        ('on', 'on'),
        ('off', 'off'),
        
    ]
    reference = models.CharField(max_length = 250,unique=True)
    statut = models.CharField(choices=statut ,max_length = 250,default='on')
    affecter = models.BooleanField(default = False)
    type = models.ForeignKey(type_tag, on_delete=models.CASCADE,blank=True,null=True)
    compte = models.ForeignKey(Compte,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.reference
    
    

class tagEmplacement(models.Model):
    """Tag assigned to locations/emplacements for scanning and audits."""
    statut = [
        ('on', 'on'),
        ('off', 'off'),
        
    ]
    reference = models.CharField(max_length = 250,unique=True)
    statut = models.CharField(choices=statut ,max_length = 250,default='on')
    affecter = models.BooleanField(default = False)
    type = models.ForeignKey(type_tag, on_delete=models.CASCADE,blank=True,null=True)
    compte = models.ForeignKey(Compte,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.reference


class TagHistory(models.Model):
    """Audit trail for tag changes on items (who changed what and when)."""
    item = models.ForeignKey(item, on_delete=models.CASCADE, related_name='tag_history')
    old_tag = models.ForeignKey(tag, on_delete=models.CASCADE, null=True, related_name='old_tag')
    new_tag = models.ForeignKey(tag, on_delete=models.CASCADE, null=True, related_name='new_tag')
    changed_by = models.ForeignKey(UserWeb, on_delete=models.CASCADE, null=True, related_name='user_changed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Item: {self.item.reference_auto}, Ancien Tag: {self.old_tag.reference if self.old_tag else 'None'}, Nouveau Tag: {self.new_tag.reference if self.new_tag else 'None'}"


class TagHistoryEmplacement(models.Model):
    """Audit trail for tag changes on locations (emplacements)."""
    emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE, related_name='tag_history_emplacement')
    old_tag = models.ForeignKey(tagEmplacement, on_delete=models.CASCADE, null=True, related_name='old_tag')
    new_tag = models.ForeignKey(tagEmplacement, on_delete=models.CASCADE, null=True, related_name='new_tag')
    changed_by = models.ForeignKey(UserWeb, on_delete=models.CASCADE, null=True, related_name='user_change')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"emplacement: {self.emplacement.nom}, Ancien Tag: {self.old_tag.reference if self.old_tag else 'None'}, Nouveau Tag: {self.new_tag.reference if self.new_tag else 'None'}"




class operation_article(models.Model):
    """Attachment and comments recorded on an item within an operation context."""
    item = models.ForeignKey(item, on_delete=models.CASCADE)
    operation = models.ForeignKey(operation, on_delete=models.CASCADE)
    prix = models.FloatField(blank=True,null=True)
    date_operation = models.DateField(blank=True,null=True)
    attachement = models.FileField(upload_to='attachmentsOperation/',blank=True,null=True)
    commentaire = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.item} - {self.operation}"


class inventaire(models.Model):
    """Inventory campaign coordinating checks for multiple emplacements/items."""
    statut = [
        ("Terminer", "Terminer"),
        ('En attente', 'En attente'),
        ("En cours", "En cours"),
    ]
    categorie = [("Location","Location"),("Zone","Zone"),("Departement","Departement"),("Emplacement","Emplacement")]
    
    nom = models.CharField(max_length=250,unique=True)
    categorie = models.CharField(max_length=255, choices=categorie)
    reference = models.CharField(max_length=250,unique=True)
    user = models.ForeignKey(UserWeb, on_delete=models.CASCADE)
    statut = models.CharField(max_length=255, choices=statut ,default='En attente' )
    date_creation = models.DateTimeField()
    date_debut = models.DateTimeField(blank=True,null=True)
    date_fin = models.DateTimeField(blank=True,null=True)
    departement= models.ForeignKey(departement, on_delete=models.CASCADE,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return self.nom
    
    
    def save(self, *args, **kwargs):
        if not self.reference:  # Générer la référence uniquement si elle est vide
            # Récupérer la référence existante la plus élevée
            last_reference = (
                inventaire.objects.filter(reference__startswith="INV-")
                .order_by('-reference')
                .values_list('reference', flat=True)
                .first()
            )
            if last_reference:
                # Extraire le numéro de la référence (ex. : PRSN-000001 -> 1)
                match = re.search(r'INV-(\d+)', last_reference)
                if match:
                    next_number = int(match.group(1)) + 1
                else:
                    next_number = 1
            else:
                next_number = 1  # Si aucune référence n'existe

            # Générer la nouvelle référence
            self.reference = f"INV-{next_number:06d}"

        super().save(*args, **kwargs)

    
    def lancer_inventaire(self, inventaire_id):
        # Récupérer l'inventaire correspondant à l'inventaire_id
        inventaire_instance = inventaire.objects.get(id=inventaire_id)
        emplacements = inventaire_emplacement.objects.filter(inventaire=inventaire_instance)
        emplacement_en_cours = emplacements.filter(statut="En cours").count()
        if emplacement_en_cours == 1:
            # Lancer l'inventaire en changeant son statut à "En cours"
            inventaire_instance.statut = "En cours"
            inventaire_instance.save()
        emplacements_terminer = emplacements.filter(statut="Terminer").count()
        if emplacements_terminer == emplacements.count():
            inventaire_instance.statut = "Terminer"
            inventaire_instance.date_fin = timezone.now()  
            inventaire_instance.save()
        return inventaire_instance



class inventaire_emplacement(models.Model):
    """Inventory state for a single emplacement within a campaign."""
    statut = [
        ("Terminer", "Terminer"),
        ("En attenter", "En attente"),
        ("En cours", "En cours"),
        
    ]
    emplacement = models.ForeignKey(emplacement, on_delete=models.CASCADE)
    inventaire = models.ForeignKey(inventaire, on_delete=models.CASCADE)
    statut = models.CharField(max_length=255, choices=statut ,default="en attente")
    affceted_at = models.ForeignKey(UserWeb, on_delete=models.CASCADE, null=True, related_name='affected_at')
    start_at = models.BooleanField(default =False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.emplacement} - {self.inventaire}"

class detail_inventaire(models.Model):
    """Inventory detail line linking an item and its observed state."""
    
    inventaire_emplacement = models.ForeignKey(inventaire_emplacement, on_delete=models.CASCADE, null=True,blank=True) 
    item = models.ForeignKey(item, on_delete=models.CASCADE)
    etat = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.item} - {self.inventaire_emplacement}"

class ArchiveItem(models.Model):
    """Archived items with comments explaining the reason/context."""
    item_archive = models.ForeignKey(item, on_delete=models.CASCADE, related_name='archive_items')
    commentaire = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    