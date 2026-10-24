from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_roles(sender, **kwargs):
    from third_side.services.roles import sync_roles

    sync_roles(sender)


class ThirdSideConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'third_side'

    def ready(self):
        import third_side.signals  # noqa:F401

        post_migrate.connect(_sync_roles, sender=self)
