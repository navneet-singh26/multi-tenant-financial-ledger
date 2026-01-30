
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from entities.models import Entity, EntityMembership

User = get_user_model()


class Command(BaseCommand):
    """Management command to create an entity."""
    
    help = 'Create a new entity with an owner'
    
    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Entity name')
        parser.add_argument('entity_type', type=str, help='Entity type (company, individual, etc.)')
        parser.add_argument('owner_email', type=str, help='Owner email address')
        parser.add_argument('--currency', type=str, default='USD', help='Default currency')
        parser.add_argument('--timezone', type=str, default='UTC', help='Timezone')
    
    def handle(self, *args, **options):
        name = options['name']
        entity_type = options['entity_type']
        owner_email = options['owner_email']
        currency = options['currency']
        timezone = options['timezone']
        
        try:
            # Get or create owner user
            owner = User.objects.get(email=owner_email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {owner_email} does not exist')
            )
            return
        
        # Create entity
        entity = Entity.objects.create(
            name=name,
            entity_type=entity_type,
            currency=currency,
            timezone=timezone,
            status='active',
            is_active=True
        )
        
        # Create owner membership
        EntityMembership.objects.create(
            entity=entity,
            user=owner,
            role='owner',
            status='active'
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created entity "{name}" with owner {owner_email}'
            )
        )