
from django.core.management.base import BaseCommand, CommandError
from entities.models import Entity
from entities.schema_manager import SchemaManager


class Command(BaseCommand):
    help = 'Delete an entity and its schema'

    def add_arguments(self, parser):
        parser.add_argument('entity_id', type=str, help='Entity ID to delete')
        parser.add_argument(
            '--keep-schema',
            action='store_true',
            help='Keep the database schema (do not drop it)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        entity_id = options['entity_id']
        keep_schema = options['keep_schema']
        force = options['force']

        try:
            entity = Entity.objects.get(id=entity_id)
        except Entity.DoesNotExist:
            raise CommandError(f"Entity with ID {entity_id} does not exist")

        # Show entity details
        self.stdout.write(f"\nEntity to delete:")
        self.stdout.write(f"  Name: {entity.name}")
        self.stdout.write(f"  ID: {entity.id}")
        self.stdout.write(f"  Type: {entity.entity_type}")
        self.stdout.write(f"  Schema: {entity.schema_name}")
        self.stdout.write(f"  Members: {entity.memberships.count()}")

        # Confirmation
        if not force:
            confirm = input(f"\nAre you sure you want to delete this entity? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING("Deletion cancelled"))
                return

        schema_name = entity.schema_name

        # Delete entity
        try:
            entity.delete()
            self.stdout.write(
                self.style.SUCCESS(f"Entity {entity.name} deleted successfully")
            )
        except Exception as e:
            raise CommandError(f"Failed to delete entity: {str(e)}")

        # Drop schema
        if not keep_schema:
            try:
                schema_manager = SchemaManager()
                schema_manager.drop_schema(schema_name)
                self.stdout.write(
                    self.style.SUCCESS(f"Schema {schema_name} dropped successfully")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Failed to drop schema: {str(e)}")
                )
        else:
            self.stdout.write(
                self.style.WARNING(f"Schema {schema_name} was kept as requested")
            )