from django.apps import AppConfig


class CentroimmuneConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'centroimmune'

    
    def ready(self):
        import centroimmune.signals  # Reemplaza 'tu_app' con el nombre de tu aplicación

