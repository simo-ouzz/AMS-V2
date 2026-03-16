from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Créer un superutilisateur si aucun superutilisateur n\'existe'

    def handle(self, *args, **kwargs):
        User = get_user_model()  # Utiliser le modèle d'utilisateur personnalisé
        if not User.objects.filter(is_superuser=True).exists():
            # Créer le superutilisateur avec un mot de passe par défaut ou défini par environnement
            email = 'admin@example.com'  # Adresse email par défaut, vous pouvez la changer
            password = 'admin1234'  # Mot de passe par défaut
            role = 'Administrateur'  # Rôle par défaut
            user = User.objects.create_superuser(
                email=email,
                role=role,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser créé : {user.email}'))
        else:
            self.stdout.write(self.style.SUCCESS('Un superutilisateur existe déjà.'))
