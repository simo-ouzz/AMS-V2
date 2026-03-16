"""
Script de gestion des opérations, réaffectations et transferts pour un item spécifique.

Usage:
    python manage.py manage_item_operations --article-code ARTL-001507 [options]

Options:
    --article-code CODE          Code de l'article à traiter (obligatoire)
    --create-operation REF       Créer une opération avec la référence spécifiée
    --reassign-tag TAG_REF       Réaffecter un nouveau tag avec la référence spécifiée
    --transfer-emplacement ID    Transférer vers un nouvel emplacement (ID)
    --transfer-departement ID    Transférer vers un nouveau département (ID)
    --transfer-personne ID       Transférer vers une nouvelle personne (ID)
    --list-items                 Lister tous les items de cet article
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from masterdata.models import (
    item, article, operation, tag, emplacement, 
    departement, Personne, TransferHistorique, Compte
)
from datetime import datetime


class Command(BaseCommand):
    help = 'Gère les opérations, réaffectations de tags et transferts pour un item spécifique'

    def add_arguments(self, parser):
        # Argument obligatoire
        parser.add_argument(
            '--article-code',
            type=str,
            required=True,
            help='Code de l\'article (ex: ARTL-001507)'
        )
        
        # Options pour les opérations
        parser.add_argument(
            '--create-operation',
            type=str,
            help='Créer une opération avec cette référence'
        )
        
        parser.add_argument(
            '--reassign-tag',
            type=str,
            help='Réaffecter ce tag (référence) au premier item de l\'article'
        )
        
        parser.add_argument(
            '--transfer-emplacement',
            type=int,
            help='ID du nouvel emplacement pour le transfert'
        )
        
        parser.add_argument(
            '--transfer-departement',
            type=int,
            help='ID du nouveau département pour le transfert'
        )
        
        parser.add_argument(
            '--transfer-personne',
            type=int,
            help='ID de la nouvelle personne pour l\'affectation'
        )
        
        parser.add_argument(
            '--list-items',
            action='store_true',
            help='Lister tous les items de cet article'
        )

    def handle(self, *args, **options):
        article_code = options['article_code']
        
        # Récupérer l'article
        try:
            art = article.objects.get(code_article=article_code)
            self.stdout.write(self.style.SUCCESS(f'\n✓ Article trouvé: {art.designation} ({art.code_article})'))
        except article.DoesNotExist:
            raise CommandError(f'Article avec le code "{article_code}" non trouvé')
        
        # Récupérer tous les items de cet article
        items = item.objects.filter(article=art).select_related(
            'article', 'emplacement', 'departement', 'affectation_personne', 'tag'
        )
        
        if not items.exists():
            raise CommandError(f'Aucun item trouvé pour l\'article {article_code}')
        
        self.stdout.write(self.style.SUCCESS(f'✓ {items.count()} item(s) trouvé(s)\n'))
        
        # Option: Lister les items
        if options['list_items']:
            self.list_items(items)
            return
        
        # Sélectionner le premier item pour les opérations
        first_item = items.first()
        self.stdout.write(self.style.WARNING(f'→ Item sélectionné: {first_item.reference_auto}'))
        self.display_item_info(first_item)
        
        # Créer une opération
        if options['create_operation']:
            self.create_operation(options['create_operation'], first_item)
        
        # Réaffecter un tag
        if options['reassign_tag']:
            self.reassign_tag(options['reassign_tag'], first_item)
        
        # Effectuer des transferts
        if any([options['transfer_emplacement'], options['transfer_departement'], options['transfer_personne']]):
            self.perform_transfer(
                first_item,
                options.get('transfer_emplacement'),
                options.get('transfer_departement'),
                options.get('transfer_personne')
            )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Toutes les opérations ont été effectuées avec succès!'))

    def list_items(self, items):
        """Liste tous les items avec leurs informations"""
        self.stdout.write(self.style.SUCCESS('=== Liste des items ===\n'))
        
        for itm in items:
            self.stdout.write(self.style.HTTP_INFO(f'\n📦 Item: {itm.reference_auto}'))
            self.display_item_info(itm)

    def display_item_info(self, itm):
        """Affiche les informations d'un item"""
        self.stdout.write(f'   Statut: {itm.statut}')
        self.stdout.write(f'   Archive: {"Oui" if itm.archive else "Non"}')
        self.stdout.write(f'   Numéro de série: {itm.numero_serie or "N/A"}')
        self.stdout.write(f'   Emplacement: {itm.emplacement.nom} (ID: {itm.emplacement.id})')
        self.stdout.write(f'   Département: {itm.departement.nom} (ID: {itm.departement.id})')
        self.stdout.write(f'   Personne affectée: {itm.affectation_personne.nom if itm.affectation_personne else "Aucune"}')
        self.stdout.write(f'   Tag: {itm.tag.reference if itm.tag else "Aucun"}')
        self.stdout.write(f'   Date affectation: {itm.date_affectation or "N/A"}')
        self.stdout.write('')

    @transaction.atomic
    def create_operation(self, reference, itm):
        """Crée une nouvelle opération"""
        self.stdout.write(self.style.HTTP_INFO(f'\n🔧 Création de l\'opération: {reference}'))
        
        try:
            # Vérifier si l'opération existe déjà
            if operation.objects.filter(reference=reference).exists():
                self.stdout.write(self.style.WARNING(f'⚠ L\'opération {reference} existe déjà'))
                return
            
            # Créer l'opération
            op = operation.objects.create(reference=reference)
            self.stdout.write(self.style.SUCCESS(f'✓ Opération créée: {op.reference} (ID: {op.id})'))
            
        except Exception as e:
            raise CommandError(f'Erreur lors de la création de l\'opération: {str(e)}')

    @transaction.atomic
    def reassign_tag(self, tag_reference, itm):
        """Réaffecte un tag à l'item"""
        self.stdout.write(self.style.HTTP_INFO(f'\n🏷️  Réaffectation du tag: {tag_reference}'))
        
        try:
            # Récupérer le tag
            try:
                new_tag = tag.objects.get(reference=tag_reference)
            except tag.DoesNotExist:
                # Créer le tag s'il n'existe pas
                self.stdout.write(self.style.WARNING(f'⚠ Tag {tag_reference} non trouvé, création...'))
                
                # Récupérer le premier compte disponible
                compte_obj = Compte.objects.first()
                if not compte_obj:
                    raise CommandError('Aucun compte disponible pour créer le tag')
                
                new_tag = tag.objects.create(
                    reference=tag_reference,
                    statut='on',
                    affecter=False,
                    compte=compte_obj
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Tag créé: {new_tag.reference}'))
            
            # Vérifier si le tag est déjà affecté à un autre item
            if new_tag.affecter and hasattr(new_tag, 'item'):
                self.stdout.write(self.style.WARNING(f'⚠ Le tag {tag_reference} est déjà affecté à un autre item'))
                self.stdout.write(f'   Item actuel: {new_tag.item.reference_auto}')
                
                # Libérer l'ancien item
                old_item = new_tag.item
                old_item.tag = None
                old_item.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Tag libéré de l\'item {old_item.reference_auto}'))
            
            # Libérer l'ancien tag de l'item si existant
            if itm.tag:
                old_tag = itm.tag
                old_tag.affecter = False
                old_tag.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Ancien tag {old_tag.reference} libéré'))
            
            # Affecter le nouveau tag
            itm.tag = new_tag
            itm.save()
            
            new_tag.affecter = True
            new_tag.save()
            
            self.stdout.write(self.style.SUCCESS(f'✓ Tag {tag_reference} affecté à l\'item {itm.reference_auto}'))
            
        except Exception as e:
            raise CommandError(f'Erreur lors de la réaffectation du tag: {str(e)}')

    @transaction.atomic
    def perform_transfer(self, itm, new_emplacement_id, new_departement_id, new_personne_id):
        """Effectue un transfert d'item"""
        self.stdout.write(self.style.HTTP_INFO(f'\n🚚 Transfert de l\'item: {itm.reference_auto}'))
        
        # Sauvegarder les anciennes valeurs
        old_emplacement = itm.emplacement
        old_departement = itm.departement
        old_personne = itm.affectation_personne
        
        transfer_data = {
            'item_transfer': itm,
            'old_emplacement': old_emplacement,
            'old_departement': old_departement,
            'old_personne': old_personne,
        }
        
        changes = []
        
        # Transfert d'emplacement
        if new_emplacement_id:
            try:
                new_emplacement_obj = emplacement.objects.get(id=new_emplacement_id)
                itm.emplacement = new_emplacement_obj
                transfer_data['new_emplacement'] = new_emplacement_obj
                changes.append(f'Emplacement: {old_emplacement.nom} → {new_emplacement_obj.nom}')
                self.stdout.write(self.style.SUCCESS(f'✓ Emplacement changé: {old_emplacement.nom} → {new_emplacement_obj.nom}'))
            except emplacement.DoesNotExist:
                raise CommandError(f'Emplacement avec l\'ID {new_emplacement_id} non trouvé')
        
        # Transfert de département
        if new_departement_id:
            try:
                new_departement_obj = departement.objects.get(id=new_departement_id)
                itm.departement = new_departement_obj
                transfer_data['new_departement'] = new_departement_obj
                changes.append(f'Département: {old_departement.nom} → {new_departement_obj.nom}')
                self.stdout.write(self.style.SUCCESS(f'✓ Département changé: {old_departement.nom} → {new_departement_obj.nom}'))
            except departement.DoesNotExist:
                raise CommandError(f'Département avec l\'ID {new_departement_id} non trouvé')
        
        # Transfert de personne
        if new_personne_id:
            try:
                new_personne_obj = Personne.objects.get(id=new_personne_id)
                itm.affectation_personne = new_personne_obj
                itm.statut = 'affecter'
                transfer_data['new_personne'] = new_personne_obj
                old_personne_name = f"{old_personne.nom}" if old_personne else "Aucune"
                changes.append(f'Personne: {old_personne_name} → {new_personne_obj.nom}')
                self.stdout.write(self.style.SUCCESS(f'✓ Personne changée: {old_personne_name} → {new_personne_obj.nom}'))
            except Personne.DoesNotExist:
                raise CommandError(f'Personne avec l\'ID {new_personne_id} non trouvé')
        
        if not changes:
            self.stdout.write(self.style.WARNING('⚠ Aucun changement à effectuer'))
            return
        
        try:
            # Sauvegarder l'item
            itm.save()
            
            # Créer l'historique du transfert
            transfer = TransferHistorique.objects.create(**transfer_data)
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Transfert enregistré (ID: {transfer.id})'))
            self.stdout.write('   Changements:')
            for change in changes:
                self.stdout.write(f'   - {change}')
            
        except Exception as e:
            raise CommandError(f'Erreur lors du transfert: {str(e)}')

