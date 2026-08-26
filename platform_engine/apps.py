from django.apps import AppConfig


class PlatformEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_engine'

    def ready(self):
        import platform_engine.signals  # noqa: F401
