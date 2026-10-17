from django.core.management.base import BaseCommand

from third_side.models import SyncedArticle
from third_side.services.translations import sync_translations


class Command(BaseCommand):
    help = (
        'Rebuild ArticleTranslation rows (and Article.original_language) from '
        'the stored Payload docs of every linked SyncedArticle. Idempotent; '
        'use it once after deploying the translation tables, since articles '
        'synced before then have no translation rows.'
    )

    def handle(self, *args, **options):
        done = skipped = 0
        for synced in SyncedArticle.objects.select_related('article').order_by('id'):
            if not synced.article_id:
                skipped += 1
                continue
            sync_translations(synced.article, synced.data)
            done += 1
        self.stdout.write(
            self.style.SUCCESS(f'Synced {done} article(s); skipped {skipped} unlinked')
        )
