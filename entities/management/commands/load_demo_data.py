
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
from entities.models import Entity, EntityMembership
from entities.schema_manager import SchemaManager

User = get_user_model()


class Command(BaseCommand):
    help = 'Load demo data for entities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            default='admin@example.com',
            help='Email of the user to assign as entity owner'
        )

    
    def handle(self, *args, **options):
        user_email = options['user_email']
        
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {user_email} does not exist')
            )
            return
        
        self.stdout.write('Loading demo entity data...')
        
        # Load fixtures
        call_command('loaddata', 'entities/fixtures/initial_data.json')
        
        # Get the demo entity
        try:
            entity = Entity.objects.get(name='Demo Company')
        except Entity.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Demo entity not found in fixtures')
            )
            return
        
        # Create schema for entity
        schema_manager = SchemaManager()
        if not schema_manager.schema_exists(entity.schema_name):
            self.stdout.write(f'Creating schema: {entity.schema_name}')
            schema_manager.create_schema(entity.schema_name)
        
        # Create or update membership
        membership, created = EntityMembership.objects.update_or_create(
            entity=entity,
            user=user,
            defaults={
                'role': 'owner',
                'status': 'active',
                'can_view_reports': True,
                'can_manage_settings': True,
                'can_manage_members': True,
                'can_create_transactions': True,
                'can_approve_transactions': True,
                'can_delete_transactions': True,
                'can_manage_accounts': True,
                'can_view_audit_logs': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created membership for {user.email}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Updated membership for {user.email}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Demo data loaded successfully!')
        )
        self.stdout.write(f'Entity ID: {entity.id}')
        self.stdout.write(f'Entity Name: {entity.name}')
        self.stdout.write(f'Schema: {entity.schema_name}')