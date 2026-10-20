from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from third_side.models import ActivityLog


class Command(BaseCommand):
    help = 'Delete activity log rows older than --days (default 365).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=365)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, days, dry_run, **options):
        cutoff = timezone.now() - timedelta(days=days)
        old = ActivityLog.objects.filter(created_at__lt=cutoff)
        count = old.count()
        if not dry_run:
            old.delete()
        verb = 'would delete' if dry_run else 'deleted'
        self.stdout.write(f'{verb} {count} activity log rows older than {days} days')
