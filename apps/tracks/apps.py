from django.apps import AppConfig


class TracksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tracks'

    def ready(self):
        from . import signals  # noqa: F401
