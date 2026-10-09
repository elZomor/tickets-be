from django.apps import AppConfig


class ThirdSideConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'third_side'

    def ready(self):
        import third_side.signals  # noqa:F401
