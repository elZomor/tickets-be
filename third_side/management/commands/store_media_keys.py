from django.core.management.base import BaseCommand

from third_side.models import (
    Article,
    ArticleTranslation,
    FestivalPost,
    FestivalPostMedia,
)
from third_side.services.media_urls import content_to_keys, to_key


class Command(BaseCommand):
    help = 'Replace saved upload URLs (possibly signed, expiring) with storage keys.'

    def handle(self, *args, **options):
        changed = 0
        for model, field in (
            (Article, 'cover_url'),
            (FestivalPost, 'poster_url'),
            (FestivalPostMedia, 'image_url'),
        ):
            for row in model.objects.exclude(**{field: ''}):
                key = to_key(getattr(row, field))
                if key != getattr(row, field):
                    model.objects.filter(pk=row.pk).update(**{field: key})
                    changed += 1
        for row in ArticleTranslation.objects.exclude(content=None):
            content = content_to_keys(row.content)
            if content != row.content:
                ArticleTranslation.objects.filter(pk=row.pk).update(content=content)
                changed += 1
        self.stdout.write(f'Updated {changed} rows.')
