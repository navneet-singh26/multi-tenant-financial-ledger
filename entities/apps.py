from django.apps import AppConfig


class EntitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entities'
    verbose_name = 'Entity Management'

    def ready(self):
        """Import signals when app is ready."""
        import entities.signals