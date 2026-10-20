import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from third_side.models import Category, NavGroup

DEFAULT_MOCK_DIR = '../../third_side_frontend/app/lib/mock'


def _load(directory, name):
    return json.loads((directory / name).read_text(encoding='utf-8'))


class Command(BaseCommand):
    help = (
        'Load only the header navigation (nav groups + categories) from the '
        'frontend mock JSON. Safe for a live database: nothing else is '
        'touched, and an existing category whose slug equals the mock slug or '
        'one of its URL segments (e.g. an existing "مسرح" for the mock '
        '"theater") is adopted, keeping its slug and name, instead of '
        'creating a duplicate. Idempotent. --dry-run prints the plan and '
        'rolls everything back.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--mock-dir', default=DEFAULT_MOCK_DIR)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        directory = Path(options['mock_dir']).resolve()
        if not directory.is_dir():
            raise CommandError(f'Mock directory not found: {directory}')
        home = _load(directory, 'home.json')
        pages = _load(directory, 'category-pages.json')
        with transaction.atomic():
            groups = self._groups(home)
            self._categories(home, pages, groups)
            if options['dry_run']:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('Dry run: nothing saved'))
            else:
                self.stdout.write(self.style.SUCCESS('Saved'))

    def _groups(self, home):
        groups = {}
        for order, raw in enumerate(home['navGroups'], start=1):
            groups[raw['id']], created = NavGroup.objects.update_or_create(
                slug=raw['id'],
                defaults={
                    'order': order,
                    'url_slug': raw['urlSlug'],
                    'label': raw['label'],
                    'tagline': raw['tagline'],
                    'description': raw['description'],
                    'image_url': raw['image'],
                },
            )
            self.stdout.write(
                f"group    {raw['id']:<10} {'created' if created else 'updated'}"
            )
        return groups

    @staticmethod
    def _existing(raw):
        candidates = {raw['slug'], *raw['urlSlug'].values()}
        return Category.objects.filter(slug__in=candidates).first()

    def _categories(self, home, pages, groups):
        group_of = {
            slug: (groups[group['id']], position)
            for group in home['navGroups']
            for position, slug in enumerate(group['categories'])
        }
        for raw in home['categories']:
            page = pages.get(raw['slug'], {})
            group, position = group_of.get(raw['slug'], (None, 0))
            fields = {
                'name_i18n': raw['name'],
                'url_slug': raw['urlSlug'],
                'tagline': raw['tagline'],
                'description': page.get('description', {}),
                'image_url': raw['image'],
                'hero_image_url': page.get('heroImage', ''),
                'order': raw['order'],
                'show_in_nav': raw['showInNav'],
                'featured': raw['featured'],
                'group': group,
                'group_order': position,
            }
            category = self._existing(raw)
            if category is None:
                category = Category.objects.create(
                    slug=raw['slug'], name=raw['name']['en'], **fields
                )
                action = 'created'
            else:
                for key, value in fields.items():
                    setattr(category, key, value)
                category.save()
                action = f'adopted existing slug={category.slug!r}'
            self.stdout.write(
                f"category {raw['slug']:<10} {action} -> "
                f"{group.slug if group else '-'}#{position}"
            )
