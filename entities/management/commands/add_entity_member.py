
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from entities.models import Entity, EntityMembership

User = get_user_model()


class Command(BaseCommand):
    help = 'Add a member to an entity'

    def add_arguments(self, parser):
        parser.add_argument('entity_id', type=str, help='Entity ID')
        parser.add_argument('user_email', type=str, help='User email address')
        parser.add_argument(
            '--role',
            type=str,
            default='member',
            choices=['owner', 'admin', 'accountant', 'member'],
            help='Member role (default: member)'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='active',
            choices=['active', 'invited', 'suspended'],
            help='Member status (default: active)'
        )

    def handle(self, *args, **options):
        entity_id = options['entity_id']
        user_email = options['user_email']
        role = options['role']
        status = options['status']

        # Get entity
        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            raise CommandError(f"Entity with ID {entity_id} does not exist")

        # Get or create user
        try:
            user = User.objects.get(email=user_email)
            self.stdout.write(f"Found existing user: {user_email}")
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=user_email,
                email=user_email
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created new user: {user_email}")
            )

        # Check if membership already exists
        existing = EntityMembership.objects.filter(
            entity=entity,
            user=user
        ).first()

        if existing:
            self.stdout.write(
                self.style.WARNING(
                    f"User {user_email} is already a member with role: {existing.role}"
                )
            )
            
            update = input("Update existing membership? (yes/no): ")
            if update.lower() != 'yes':
                self.stdout.write("Operation cancelled")
                return
            
            existing.role = role
            existing.status = status
            existing.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated membership for {user_email} to role: {role}, status: {status}"
                )
            )
        else:
            # Create new membership
            membership = EntityMembership.objects.create(
                entity=entity,
                user=user,
                role=role,
                status=status
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Added {user_email} to {entity.name} as {role}"
                )
            )