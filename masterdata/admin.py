"""Admin configuration for the masterdata app.

This module organizes model registrations, import/export resources and custom admin
behaviors. Keep classes small and focused; prefer read-only computed columns and
avoid heavy business logic in the admin.
"""
from django.contrib import admin
from masterdata.forms import TagEmplacementForm
from masterdata.models import *
from django.contrib.auth.admin import UserAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from import_export import resources, fields, widgets

# Register your models here.
from django.contrib.admin import AdminSite

from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib.auth.models import Group

from django.templatetags.static import static

from masterdata.views import assign_groups_view

# from masterdata.views import UserGroupAssignmentAdminView


class PermissionAdminSite(admin.ModelAdmin):
    list_display = ('name','codename','get_content_type')
    # list_filter = ('name',)
    search_fields = ('name', 'codename',)
    
    def get_content_type(self, obj):
        if obj.content_type:
            return obj.content_type.model
        return None
    get_content_type.short_description = 'content_type'

admin.site.register(Permission, PermissionAdminSite)

class CustomAdminSite(AdminSite):
    def get_media(self):
        media = super().get_media()
        media.add_css(static('custom_admin.css'))  # Include your custom CSS
        return media

admin_site = CustomAdminSite(name='custom_admin')



class CompteAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'code_compte', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('libelle', 'code_compte')

admin.site.register(Compte, CompteAdmin)

class UserWebAdmin(UserAdmin):
    list_display = ('nom', 'prenom', 'email', 'role', 'type', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')

    # Exclure 'compte' pour le cacher dans les formulaires
    exclude = ('compte',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('role', 'type', 'is_staff', 'groups')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('nom', 'prenom', 'email', 'password1', 'password2', 'role', 'type', 'is_staff', 'groups')}
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        # Obtenir le formulaire et exclure le champ 'compte'
        form = super().get_form(request, obj, **kwargs)
        form.base_fields.pop('compte', None)  # Exclure le champ compte du formulaire
        return form

    def save_model(self, request, obj, form, change):
        print(self.get_compte_for_user(request.user))
        obj.compte = self.get_compte_for_user(request.user)
        super().save_model(request, obj, form, change)

    def get_compte_for_user(self, user):
        # Logique pour récupérer le compte de l'utilisateur
        # Supposons que vous ayez une méthode pour le faire
        return user.compte  # Remplacez cette ligne par la logique appropriée
    
    
    def get_queryset(self, request):
        # Filtrer uniquement les super utilisateurs
        queryset = super().get_queryset(request)
        return queryset.filter(is_superuser=False)

admin.site.register(UserWeb, UserWebAdmin)




class SuperUserAdmin(UserAdmin):
    list_display = ('nom', 'prenom', 'email', 'role', 'type', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('role', 'type', 'is_active', 'is_staff', 'is_superuser', 'groups')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('nom', 'prenom', 'email', 'password1', 'password2', 'compte', 'role', 'type', 'is_active', 'is_staff', 'is_superuser', 'groups')}
        ),
    )

    def get_queryset(self, request):
        # Filtrer uniquement les super utilisateurs
        queryset = super().get_queryset(request)
        return queryset.filter(is_superuser=True)

    def save_model(self, request, obj, form, change):
        # Forcer is_superuser à True lors de la création
        obj.is_superuser = True
        super().save_model(request, obj, form, change)

# Enregistrement du proxy model dans l'admin Django
admin.site.register(SuperUserProxy, SuperUserAdmin)



# class UserMobileAdmin(UserAdmin):
#     list_display = ('email', 'compte', 'history')
#     list_filter = ('compte',)
#     search_fields = ('email',)
#     ordering = ('email',)

# admin.site.register(UserMobile, UserMobileAdmin)


class CategorieResource(resources.ModelResource):
    nom = fields.Field(column_name='libelle', attribute='libelle', widget=widgets.CharWidget())
    
    class Meta:
        model = categorie
        fields = ('libelle',)
        exclude = ('id',)
        import_id_fields = ()
    
    
    

class CategorieAdmin(ImportExportModelAdmin):
    resource_class = CategorieResource
    list_display = ('libelle', 'reference', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('libelle', 'reference')
    exclude = ('reference',)

    class Meta:
        verbose_name = "Catégorie"
        description = "Gérez les catégories de familles."
        
    
    
admin.site.register(categorie, CategorieAdmin)



class MarqueResource(resources.ModelResource):
    nom = fields.Field(column_name='nom', attribute='nom', widget=widgets.CharWidget())
    
    class Meta:
        model = marque
        fields = ('nom',)
        exclude = ('id',)
        import_id_fields = ()
    
    

class MarqueAdmin(ImportExportModelAdmin):
    resource_class = MarqueResource
    list_display = ('nom', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('nom',)

admin.site.register(marque, MarqueAdmin)
class ProduitResource(resources.ModelResource):
    libelle = fields.Field(column_name='libelle', attribute='libelle', widget=widgets.CharWidget())
    categorie = fields.Field(column_name='categorie', attribute='categorie', widget=widgets.ForeignKeyWidget(categorie, 'libelle'))
    duree_amourtissement = fields.Field(column_name='duree_amourtissement', attribute='duree_amourtissement', widget=widgets.IntegerWidget())
    statut = fields.Field(column_name='statut', attribute='statut', widget=widgets.CharWidget())

    class Meta:
        model = produit
        fields = ('libelle','categorie', 'duree_amourtissement', 'statut')
        exclude = ('id',)
        import_id_fields = ()

    def before_import_row(self, row, **kwargs):
        # Chercher l'objet categorie à partir du libellé dans la ligne d'importation
        categorie_name = row.get('categorie')
        try:
            categorie_obj = categorie.objects.get(libelle=categorie_name)
            row['categorie'] = categorie_obj
        except categorie.DoesNotExist:
            raise ValueError(f"La catégorie '{categorie_name}' n'existe pas dans la base de données.")

class ProduitAdmin(ImportExportModelAdmin):
    resource_class = ProduitResource
    list_display = ('libelle', 'code_produit','statut','duree_amourtissement', 'categorie', 'created_at', 'updated_at')
    list_filter = ('categorie', 'created_at', 'updated_at')
    search_fields = ('libelle', 'code_produit')
    exclude = ('code_produit',)
    class Meta:
        description = "Gérez les familles dans différentes catégories."

admin.site.register(produit, ProduitAdmin)




class OperationAdmin(admin.ModelAdmin):
    list_display = ('reference','created_at', 'updated_at')
    list_filter = ('reference', 'created_at', 'updated_at')

admin.site.register(operation, OperationAdmin)



class NatureResource(resources.ModelResource):
    libelle = fields.Field(column_name='libelle', attribute='libelle', widget=widgets.CharWidget())
    
    class Meta:
        model = nature
        fields = ('libelle',)
        exclude = ('id',)
        import_id_fields = ()
    
class NatureAdmin(ImportExportModelAdmin):
    resource_class = NatureResource
    list_display = ('libelle', 'reference', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('libelle', 'reference')
    exclude = ('reference',)

admin.site.register(nature, NatureAdmin)


class FournisseurResource(resources.ModelResource):
    nom = fields.Field(column_name='nom', attribute='nom', widget=widgets.CharWidget())
    class Meta:
        model = fournisseur
        fields = ('nom',)
        exclude = ('id',)
        import_id_fields = ()
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = None  # Ajouter un attribut pour stocker l'utilisateur

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        # Stocker l'utilisateur authentifié dans self.current_user
        self.current_user = kwargs.get('user')
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import.")
    
    def before_import_row(self, row, **kwargs):
        # Vérifier que l'utilisateur est disponible ici
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import_row.")

    def before_save_instance(self, instance, using_transactions, dry_run, **kwargs):
        # Utiliser l'utilisateur stocké dans self.current_user
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_save_instance.")
        if hasattr(self.current_user, 'compte'):
            instance.compte = self.current_user.compte
        else:
            raise ValueError("L'utilisateur n'a pas de compte associé.")
        super().before_save_instance(instance, using_transactions, dry_run, **kwargs)



class FournisseurAdmin(ImportExportModelAdmin):
    resource_class = FournisseurResource
    list_display = ('nom','reference', 'created_at', 'updated_at')
    list_filter = ('nom','created_at', 'updated_at')
    search_fields = ('nom', 'reference',)
    exclude = ('reference', 'ice', 'tel', 'adresse', 'compte', 'created_at', 'updated_at', 'history')

    def get_form(self, request, obj=None, **kwargs):
        # Obtenir le formulaire et exclure le champ 'compte'
        form = super().get_form(request, obj, **kwargs)
        form.base_fields.pop('compte', None)  # Exclure le champ compte du formulaire
        return form

    def save_model(self, request, obj, form, change):
        print(self.get_compte_for_user(request.user))
        obj.compte = self.get_compte_for_user(request.user)
        super().save_model(request, obj, form, change)

    def get_compte_for_user(self, user):
        # Logique pour récupérer le compte de l'utilisateur
        # Supposons que vous ayez une méthode pour le faire
        return user.compte  # Remplacez cette ligne par la logique appropriée

admin.site.register(fournisseur, FournisseurAdmin)












class PersonneResource(resources.ModelResource):
    nom = fields.Field(column_name='nom', attribute='nom', widget=widgets.CharWidget())
    prenom = fields.Field(column_name='prenom', attribute='prenom', widget=widgets.CharWidget())
    class Meta:
        model = Personne
        fields = ('nom','prenom')
        exclude = ('id',)
        import_id_fields = ()
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = None  # Ajouter un attribut pour stocker l'utilisateur

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        # Stocker l'utilisateur authentifié dans self.current_user
        self.current_user = kwargs.get('user')
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import.")
    
    def before_import_row(self, row, **kwargs):
        # Vérifier que l'utilisateur est disponible ici
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import_row.")

    def before_save_instance(self, instance, using_transactions, dry_run, **kwargs):
        # Utiliser l'utilisateur stocké dans self.current_user
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_save_instance.")
        if hasattr(self.current_user, 'compte'):
            instance.compte = self.current_user.compte
        else:
            raise ValueError("L'utilisateur n'a pas de compte associé.")
        super().before_save_instance(instance, using_transactions, dry_run, **kwargs)






class PersonneAdmin(ImportExportModelAdmin):
    resource_class = PersonneResource
    list_display = ('nom', 'prenom', 'gender', 'created_at', 'updated_at')
    list_filter = ('nom', 'prenom', 'gender')
    search_fields = ('nom', 'prenom', 'gender')
    exclude = ('reference',)
    def get_form(self, request, obj=None, **kwargs):
        # Obtenir le formulaire et exclure le champ 'compte'
        form = super().get_form(request, obj, **kwargs)
        form.base_fields.pop('compte', None)  # Exclure le champ compte du formulaire
        return form

    def save_model(self, request, obj, form, change):
        print(self.get_compte_for_user(request.user))
        obj.compte = self.get_compte_for_user(request.user)
        super().save_model(request, obj, form, change)

    def get_compte_for_user(self, user):
        # Logique pour récupérer le compte de l'utilisateur
        # Supposons que vous ayez une méthode pour le faire
        return user.compte  # Remplacez cette ligne par la logique appropriée

admin.site.register(Personne, PersonneAdmin)
from django.contrib import admin, messages
from django.db.models import signals

class DepartementResource(resources.ModelResource):
    nom = fields.Field(column_name='nom', attribute='nom', widget=widgets.CharWidget())
    # reference = fields.Field(column_name='reference', attribute='reference', widget=widgets.CharWidget())

    class Meta:
        model = departement
        fields = ('nom',)
        exclude = ('id',)
        import_id_fields = ()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = None  # Ajouter un attribut pour stocker l'utilisateur

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        # Stocker l'utilisateur authentifié dans self.current_user
        self.current_user = kwargs.get('user')
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import.")
    
    def before_import_row(self, row, **kwargs):
        # Vérifier que l'utilisateur est disponible ici
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import_row.")

    def before_save_instance(self, instance, using_transactions, dry_run, **kwargs):
        # Utiliser l'utilisateur stocké dans self.current_user
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_save_instance.")
        if hasattr(self.current_user, 'compte'):
            instance.compte = self.current_user.compte
        else:
            raise ValueError("L'utilisateur n'a pas de compte associé.")
        super().before_save_instance(instance, using_transactions, dry_run, **kwargs)




class DepartementAdmin(ImportExportModelAdmin):
    resource_class = DepartementResource
    list_display = ('nom', 'reference','compte', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('nom', 'reference')
    exclude = ('reference',)
    def get_form(self, request, obj=None, **kwargs):
        # Obtenir le formulaire et exclure le champ 'compte'
        form = super().get_form(request, obj, **kwargs)
        form.base_fields.pop('compte', None)  # Exclure le champ compte du formulaire
        return form

    def save_model(self, request, obj, form, change): 
        print(self.get_compte_for_user(request.user))
        obj.compte = self.get_compte_for_user(request.user)
        super().save_model(request, obj, form, change)

    def get_compte_for_user(self, user):
        # Logique pour récupérer le compte de l'utilisateur
        # Supposons que vous ayez une méthode pour le faire
        return user.compte  # Remplacez cette ligne par la logique appropriée

admin.site.register(departement, DepartementAdmin)




class LocationResource(resources.ModelResource):
    nom = fields.Field(column_name='nom', attribute='nom', widget=widgets.CharWidget())
    # reference = fields.Field(column_name='reference', attribute='reference', widget=widgets.CharWidget())

    class Meta:
        model = location
        fields = ('nom',)
        exclude = ('id',)
        import_id_fields = ()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = None  # Ajouter un attribut pour stocker l'utilisateur

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        # Stocker l'utilisateur authentifié dans self.current_user
        self.current_user = kwargs.get('user')
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import.")
    
    def before_import_row(self, row, **kwargs):
        # Vérifier que l'utilisateur est disponible ici
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import_row.")

    def before_save_instance(self, instance, using_transactions, dry_run, **kwargs):
        # Utiliser l'utilisateur stocké dans self.current_user
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_save_instance.")
        if hasattr(self.current_user, 'compte'):
            instance.compte = self.current_user.compte
        else:
            raise ValueError("L'utilisateur n'a pas de compte associé.")
        super().before_save_instance(instance, using_transactions, dry_run, **kwargs)




class LocationAdmin(ImportExportModelAdmin):
    resource_class = LocationResource
    list_display = ('nom', 'reference', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('nom', 'reference')
    exclude = ('reference',)
    def get_form(self, request, obj=None, **kwargs):
        # Obtenir le formulaire et exclure le champ 'compte'
        form = super().get_form(request, obj, **kwargs)
        form.base_fields.pop('compte', None)  # Exclure le champ compte du formulaire
        return form

    def save_model(self, request, obj, form, change): 
        print(self.get_compte_for_user(request.user))
        obj.compte = self.get_compte_for_user(request.user)
        super().save_model(request, obj, form, change)

    def get_compte_for_user(self, user):
        # Logique pour récupérer le compte de l'utilisateur
        # Supposons que vous ayez une méthode pour le faire
        return user.compte  # Remplacez cette ligne par la logique appropriée

admin.site.register(location, LocationAdmin)

class ZoneResource(resources.ModelResource):
    nom = fields.Field(column_name='nom', attribute='nom', widget=widgets.CharWidget())
    location = fields.Field(column_name='location', attribute='location', widget=widgets.ForeignKeyWidget(location, 'nom'))

    class Meta:
        model = zone
        fields = ('nom', 'location',)
        exclude = ('id',)
        import_id_fields = ()

    def before_import_row(self, row, **kwargs):
        # Chercher l'objet location à partir du nom dans la ligne d'importation
        location_name = row.get('location')
        # print(location_name)
        try:
            location_obj = location.objects.get(nom=location_name)
            # print(location_obj)
            row['location'] = location_obj
        except location.DoesNotExist:
            raise ValueError(f"La localisation '{location_name}' n'existe pas dans la base de données.")

class ZoneAdmin(ImportExportModelAdmin):
    resource_class = ZoneResource
    list_display = ('nom', 'location', 'reference','created_at', 'updated_at')
    list_filter = ('location', 'created_at', 'updated_at')
    search_fields = ('nom', 'reference')
    exclude = ('reference',)

admin.site.register(zone, ZoneAdmin)





class EmplacementResource(resources.ModelResource):
    nom = fields.Field(column_name='nom', attribute='nom', widget=widgets.CharWidget())
    zone = fields.Field(column_name='zone', attribute='zone', widget=widgets.ForeignKeyWidget(zone, 'nom'))

    class Meta:
        model = emplacement
        fields = ('nom', 'zone',)
        exclude = ('id',)
        import_id_fields = ()

    def before_import_row(self, row, **kwargs):
        zone_name = row.get('zone')
        try:
            zone_obj = zone.objects.get(nom=zone_name)
            row['zone'] = zone_obj
        except zone.DoesNotExist:
            raise ValueError(f"La zone '{zone_name}' n'existe pas dans la base de données.")


class EmplacementAdmin(ImportExportModelAdmin):
    resource_class = EmplacementResource
    list_display = ('nom', 'zone', 'reference','created_at', 'updated_at')
    list_filter = ('zone', 'created_at', 'updated_at')
    search_fields = ('nom', 'reference', 'code_barre')
    exclude = ('reference','tag',)
admin.site.register(emplacement, EmplacementAdmin)

# class EmplacementHistoryAdmin(SimpleHistoryAdmin):
#     list_display = ["id", "name", "status"]
#     history_list_display = ["status"]
#     search_fields = ['name', 'user__username']

# admin.site.register(emplacement, EmplacementHistoryAdmin)

class Type_tag_Admin(admin.ModelAdmin):
    list_display = ('nom','created_at', 'updated_at')
    list_filter = ('nom', 'created_at', 'updated_at')
    search_fields = ('nom',)

admin.site.register(type_tag, Type_tag_Admin)


from import_export import resources, fields, widgets
from .models import tag, type_tag

class TagResource(resources.ModelResource):
    type = fields.Field(
        column_name='type',
        attribute='type',
        widget=widgets.ForeignKeyWidget(type_tag, 'nom')
    )

    class Meta:
        model = tag
        fields = ('reference', 'type')  # Champs d'importation
        exclude = ('id',)  # Exclure les champs non nécessaires
        import_id_fields = ('reference',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = None  # Ajouter un attribut pour stocker l'utilisateur

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        # Stocker l'utilisateur authentifié dans self.current_user
        self.current_user = kwargs.get('user')
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import.")

    def before_import_row(self, row, **kwargs):
        # Vérifier que l'utilisateur est disponible ici
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import_row.")

        type_name = row.get('type')
        try:
            tag_type = type_tag.objects.get(nom=type_name)
            row['type'] = tag_type
        except type_tag.DoesNotExist:
            raise ValueError(f"Le type '{type_name}' n'existe pas dans la base de données.")

    def before_save_instance(self, instance, using_transactions, dry_run, **kwargs):
        # Utiliser l'utilisateur stocké dans self.current_user
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_save_instance.")
        if hasattr(self.current_user, 'compte'):
            instance.compte = self.current_user.compte
        else:
            raise ValueError("L'utilisateur n'a pas de compte associé.")
        super().before_save_instance(instance, using_transactions, dry_run, **kwargs)



class TagAdmin(ImportExportModelAdmin):
    resource_class = TagResource
    list_display = ('reference', 'statut', 'get_Item_code', 'affecter', 'get_type_code', 'created_at', 'updated_at')
    list_filter = ('reference', 'statut', 'created_at', 'updated_at')
    search_fields = ('reference', 'statut')

    def get_import_context(self, request):
        # Obtenir le contexte d'importation et ajouter l'utilisateur
        context = super().get_import_context(request)
        context['user'] = request.user  # Transmettez l'utilisateur authentifié dans le contexte
        return context

    def get_Item_code(self, obj):
        if obj.item:
            return obj.item.article.designation
        return None
    get_Item_code.short_description = 'item'

    def get_type_code(self, obj):
        if obj.type:
            return obj.type.nom
        return None
    get_type_code.short_description = 'type'

    def get_form(self, request, obj=None, **kwargs):
        # Obtenir le formulaire et exclure le champ 'compte'
        form = super().get_form(request, obj, **kwargs)
        form.base_fields.pop('compte', None)  # Exclure le champ 'compte' du formulaire
        return form

    def save_model(self, request, obj, form, change):
        # Assigner le compte à l'objet lors de la sauvegarde
        obj.compte = self.get_compte_for_user(request.user)
        super().save_model(request, obj, form, change)

    def get_compte_for_user(self, user):
        # Logique pour récupérer le compte de l'utilisateur
        return user.compte  # Remplacez cette ligne par la logique appropriée

admin.site.register(tag, TagAdmin)





class ReferenceValidationError(Exception):
    """Exception personnalisée pour les erreurs de validation des références."""
    def __init__(self, invalid_references):
        self.invalid_references = invalid_references
        super().__init__("Références invalides.")

    def get_message(self):
        """Retourne un message utilisateur clair."""
        return (
            "Erreur lors de l'importation : Les références suivantes ne sont pas valides "
            f"(elles doivent commencer par '4C4F43') : {', '.join(self.invalid_references)}"
        )


# Resource pour gérer l'import/export
class TagEmplacementResource(resources.ModelResource):
    type = fields.Field(
        column_name='type',
        attribute='type',
        widget=widgets.ForeignKeyWidget(type_tag, 'nom')
    )

    class Meta:
        model = tagEmplacement
        fields = ('reference', 'type')
        import_id_fields = ()
        exclude = ('id',)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = None  # Ajouter un attribut pour stocker l'utilisateur
   
    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        errors = []

        # Vérifier que toutes les références commencent par '4C4F43'
        for i, row in enumerate(dataset.dict):
            reference = row.get('reference')
            if not reference.startswith('4C4F43'):
                errors.append(f"Ligne {i + 1}: La référence '{reference}' ne commence pas par '4C4F43'.")

        if errors:
            # Lever une exception avec uniquement les erreurs de référence sans chemin d'appel
            raise ValueError("\n".join(errors))
        
        self.current_user = kwargs.get('user')
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import.")
    
    def before_import_row(self, row, **kwargs):
        # Vérifier que l'utilisateur est disponible ici
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_import_row.")

        type_name = row.get('type')
        try:
            tag_type = type_tag.objects.get(nom=type_name)
            row['type'] = tag_type
        except type_tag.DoesNotExist:
            raise ValueError(f"Le type '{type_name}' n'existe pas dans la base de données.")

    def before_save_instance(self, instance, using_transactions, dry_run, **kwargs):
        # Utiliser l'utilisateur stocké dans self.current_user
        if not self.current_user:
            raise ValueError("Utilisateur non trouvé dans before_save_instance.")
        if hasattr(self.current_user, 'compte'):
            instance.compte = self.current_user.compte
        else:
            raise ValueError("L'utilisateur n'a pas de compte associé.")
        super().before_save_instance(instance, using_transactions, dry_run, **kwargs)

from import_export.admin import ImportExportModelAdmin
from django.contrib import messages


class TagEmplacementAdmin(ImportExportModelAdmin):
    form = TagEmplacementForm
    resource_class = TagEmplacementResource
    list_display = ('reference', 'statut', 'get_emplacement_nom', 'affecter', 'type', 'created_at', 'updated_at')
    list_filter = ('reference', 'statut', 'created_at', 'updated_at')
    search_fields = ('reference', 'statut')
    exclude = ('compte',)
    
    def get_import_context(self, request):
        # Obtenir le contexte d'importation et ajouter l'utilisateur
        context = super().get_import_context(request)
        context['user'] = request.user  # Transmettez l'utilisateur authentifié dans le contexte
        return context
    
    def get_form(self, request, obj=None, **kwargs):
        # Obtenir le formulaire et exclure le champ 'compte'
        form = super().get_form(request, obj, **kwargs)
        form.base_fields.pop('compte', None)  # Exclure le champ 'compte' du formulaire
        return form

    def save_model(self, request, obj, form, change):
        # Assigner le compte à l'objet lors de la sauvegarde
        obj.compte = self.get_compte_for_user(request.user)
        super().save_model(request, obj, form, change)

    def get_compte_for_user(self, user):
        # Logique pour récupérer le compte de l'utilisateur
        return user.compte  # Remplacez cette ligne par la logique appropriée

    def get_emplacement_nom(self, obj):
        if obj.emplacement:
            return obj.emplacement.nom
        return None
    get_emplacement_nom.short_description = 'emplacement'

    def import_action(self, request, *args, **kwargs):
        """
        Cette méthode surcharge l'action d'importation pour capturer les erreurs et afficher
        uniquement un message d'erreur personnalisé sans traceback complet.
        """
        try:
            # Appel de l'action d'importation de la classe parente
            result = super().import_action(request, *args, **kwargs)
            self.message_user(request, "Importation réussie !", level=messages.SUCCESS)
            return result
        except ValueError as e:
            # Afficher uniquement le message d'erreur sans traceback complet
            error_message = str(e)
            self.message_user(request, f"Erreur lors de l'importation : {error_message}", level=messages.ERROR)
            return None
admin.site.register(tagEmplacement, TagEmplacementAdmin)




# class EmplacementsTagAdmin(admin.ModelAdmin):
#     readonly_fields = ['nom', 'zone', 'reference', 'code_barre', 'created_at', 'updated_at']
#     list_filter = ('nom',)
#     fields = ['tag']

#     def has_add_permission(self, request):
#         return False

#     def has_delete_permission(self, request, obj=None):
#         return False

# admin.site.register(EmplacementTag, EmplacementsTagAdmin)
# admin.site.set_menu_order([Compte,UserWeb,location,zone,emplacement,departement,categorie,produit,type_tag,tag])

# class EmplacementsTagAdmin(admin.ModelAdmin):
#     readonly_fields = ['nom', 'zone', 'reference', 'code_barre', 'created_at', 'updated_at']
#     list_filter = ('nom',)
#     fields = ['tag']

#     def has_add_permission(self, request):
#         return False

#     def has_delete_permission(self, request, obj=None):
#         return False

# admin.site.register(EmplacementTag, EmplacementsTagAdmin)
# admin.site.set_menu_order([Compte,UserWeb,location,zone,emplacement,departement,categorie,produit,type_tag,tag])