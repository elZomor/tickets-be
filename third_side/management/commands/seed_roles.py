from django.core.management.base import BaseCommand, CommandError

from third_side.services.roles import ROLES, sync_roles


class Command(BaseCommand):
    help = 'Create or update the staff role groups and their permissions.'

    def handle(self, *args, **options):
        missing = sync_roles()
        for name, codenames in ROLES.items():
            self.stdout.write(f'{name}: {len(codenames)} permissions')
        if missing:
            raise CommandError(f'Unknown permissions: {missing}')
