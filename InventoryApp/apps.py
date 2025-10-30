from django.apps import AppConfig
from django.db.models.signals import post_migrate

class InventoryAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'InventoryApp'

    def ready(self):
        try:
            # Import signal handlers
            import InventoryApp.signals
            
            # Connect post_migrate handler for group creation
            post_migrate.connect(self._create_groups, sender=self)
        except ImportError:
            pass

    def _create_groups(self, sender, **kwargs):
        from .utils import create_default_groups
        create_default_groups()
