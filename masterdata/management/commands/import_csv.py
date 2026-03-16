import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
class Command(BaseCommand):
    help = "Import CSV data into auth_permission, auth_group, and auth_group_permissions tables"
    @transaction.atomic
    def handle(self, *args, **kwargs):
        # Define file paths
        permission_file = os.path.join(settings.PERMISSION_GROUP, 'permissions.csv')
        group_file = os.path.join(settings.PERMISSION_GROUP, 'groupe.csv')
        group_permission_file = os.path.join(settings.PERMISSION_GROUP, 'auth_group_permissions.csv')


        # Clear existing data
        self.stdout.write("Clearing existing permissions and groups...")
        Permission.objects.all().delete()
        Group.objects.all().delete()

        # Import auth_permission
        self.stdout.write("Importing auth_permission...")
        try:
            with open(permission_file, 'r') as file:
                reader = csv.DictReader(file)
                permissions = [
                    Permission(
                        id=row['id'],
                        name=row['name'],
                        content_type_id=row['content_type_id'],
                        codename=row['codename']
                    )
                    for row in reader
                ]
                Permission.objects.bulk_create(permissions)
            self.stdout.write("auth_permission imported successfully.")
        except FileNotFoundError:
            self.stderr.write(f"Error: {permission_file} not found.")
            return
        except KeyError as e:
            self.stderr.write(f"Error: Missing column {e} in {permission_file}.")
            return

        # Import auth_group
        self.stdout.write("Importing auth_group...")
        try:
            with open(group_file, 'r') as file:
                reader = csv.DictReader(file)
                groups = [
                    Group(
                        id=row['id'],
                        name=row['name']
                    )
                    for row in reader
                ]
                Group.objects.bulk_create(groups)
            self.stdout.write("auth_group imported successfully.")
        except FileNotFoundError:
            self.stderr.write(f"Error: {group_file} not found.")
            return
        except KeyError as e:
            self.stderr.write(f"Error: Missing column {e} in {group_file}.")
            return

        # Import auth_group_permissions
        self.stdout.write("Importing auth_group_permissions...")
        try:
            with open(group_permission_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        group = Group.objects.get(id=row['group_id'])
                        permission = Permission.objects.get(id=row['permission_id'])
                        group.permissions.add(permission)
                    except KeyError as e:
                        self.stderr.write(f"Error: Missing column {e} in {group_permission_file}.")
                        return
                    except ObjectDoesNotExist:
                        self.stderr.write(f"Error: Group or permission with specified ID does not exist.")
                        return
            self.stdout.write("auth_group_permissions imported successfully.")
        except FileNotFoundError:
            self.stderr.write(f"Error: {group_permission_file} not found.")
            return

        self.stdout.write("CSV data imported successfully!")
