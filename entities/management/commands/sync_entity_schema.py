
from django.core.management.base import BaseCommand
from entities.models import Entity
from entities.schema_manager import SchemaManager


class Command(BaseCommand):
    """Management command to sync entity schemas."""
    
    help = 'Sync database schemas for all entities'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-missing',
            action='store_true',
            help='Create schemas for entities that are missing them'
        )
        parser.add_argument(
            '--drop-orphaned',
            action='store_true',
            help='Drop schemas that have no corresponding entity'
        )
    
    def handle(self, *args, **options):
        schema_manager = SchemaManager()
        
        if options['create_missing']:
            self.stdout.write('Creating missing schemas...')
            entities = Entity.objects.all()
            
            for entity in entities:
                if not schema_manager.schema_exists(entity.schema_name):
                    try:
                        schema_manager.create_schema(entity.schema_name)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created schema for entity: {entity.name}'
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Failed to create schema for {entity.name}: {str(e)}'
                            )
                        )
        
        if options['drop_orphaned']:
            self.stdout.write('Dropping orphaned schemas...')
            all_schemas = schema_manager.list_entity_schemas()
            entity_schemas = set(Entity.objects.values_list('schema_name', flat=True))
            
            orphaned = set(all_schemas) - entity_schemas
            
            for schema_name in orphaned:
                try:
                    schema_manager.drop_schema(schema_name)
                    self.stdout.write(
                        self.style.SUCCESS(f'Dropped orphaned schema: {schema_name}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to drop schema {schema_name}: {str(e)}'
                        )
                    )
        
        self.stdout.write(self.style.SUCCESS('Schema sync completed'))