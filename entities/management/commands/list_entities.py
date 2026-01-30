
from django.core.management.base import BaseCommand
from entities.models import Entity


class Command(BaseCommand):
    """Management command to list all entities."""
    
    help = 'List all entities'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active entities'
        )
    
    def handle(self, *args, **options):
        queryset = Entity.objects.all()
        
        if options['active_only']:
            queryset = queryset.filter(is_active=True)
        
        self.stdout.write(self.style.SUCCESS(f'Total entities: {queryset.count()}\n'))
        
        for entity in queryset:
            member_count = entity.memberships.filter(status='active').count()
            self.stdout.write(
                f'ID: {entity.id}\n'
                f'Name: {entity.name}\n'
                f'Type: {entity.entity_type}\n'
                f'Status: {entity.status}\n'
                f'Active: {entity.is_active}\n'
                f'Members: {member_count}\n'
                f'Created: {entity.created_at}\n'
                f'{"-" * 50}'
            )