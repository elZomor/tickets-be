import json
import re
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from third_side.i18n import LOCALES
from third_side.models import (
    AboutPage,
    Ad,
    Article,
    ArticleTranslation,
    Category,
    Critic,
    NavGroup,
    SiteSettings,
    Tag,
)
from third_side.models.Article import ArticleStatus

DEFAULT_MOCK_DIR = '../../third_side_frontend/app/lib/mock'


def _load(directory, name):
    return json.loads((directory / name).read_text(encoding='utf-8'))


class Command(BaseCommand):
    help = (
        'Seed the Third Side content from the frontend mock JSON, so API '
        'responses can be diffed against the mocks. Idempotent.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--mock-dir', default=DEFAULT_MOCK_DIR)

    def handle(self, *args, **options):
        directory = Path(options['mock_dir']).resolve()
        if not directory.is_dir():
            raise CommandError(f'Mock directory not found: {directory}')
        home = _load(directory, 'home.json')
        pages = _load(directory, 'category-pages.json')
        bodies = _load(directory, 'article-bodies.json')
        languages = _load(directory, 'article-languages.json')

        self._site(home)
        writers = _load(directory, 'writers.json')['writers']
        groups = self._groups(home)
        categories = self._categories(home, pages, groups)
        count = self._articles(home, pages, bodies, languages, categories)
        self._writers(writers, categories)
        self._about(_load(directory, 'about.json'))
        self._ads(_load(directory, 'ads.json')['ads'])
        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {len(groups)} groups, {len(categories)} categories, '
                f'{count} articles from {directory}'
            )
        )

    def _site(self, home):
        hero = home['hero']
        site = home['site']
        settings = SiteSettings.objects.first() or SiteSettings()
        settings.hero = {
            'image': hero['image'],
            'title': hero['title'],
            'subtitle': hero['subtitle'],
            'cta_url': hero['ctaUrl'],
        }
        settings.contact = site['contact']
        settings.social = site['social']
        settings.sponsors = site['sponsors']
        settings.save()

    def _groups(self, home):
        groups = {}
        for order, raw in enumerate(home['navGroups'], start=1):
            groups[raw['id']], _ = NavGroup.objects.update_or_create(
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
        return groups

    def _categories(self, home, pages, groups):
        group_of = {
            slug: (groups[group['id']], position)
            for group in home['navGroups']
            for position, slug in enumerate(group['categories'])
        }
        categories = {}
        for raw in home['categories']:
            page = pages.get(raw['slug'], {})
            categories[raw['slug']], _ = Category.objects.update_or_create(
                slug=raw['slug'],
                defaults={
                    'name': raw['name']['en'],
                    'name_i18n': raw['name'],
                    'url_slug': raw['urlSlug'],
                    'tagline': raw['tagline'],
                    'description': page.get('description', {}),
                    'image_url': raw['image'],
                    'hero_image_url': page.get('heroImage', ''),
                    'order': raw['order'],
                    'show_in_nav': raw['showInNav'],
                    'featured': raw['featured'],
                    'group': group_of.get(raw['slug'], (None, 0))[0],
                    'group_order': group_of.get(raw['slug'], (None, 0))[1],
                },
            )
        return categories

    def _articles(self, home, pages, bodies, languages, categories):
        raws = {}
        featured = set()
        for page in pages.values():
            raws[page['featured']['slug']['en']] = page['featured']
            featured.add(page['featured']['slug']['en'])
            for raw in page['articles']:
                raws.setdefault(raw['slug']['en'], raw)
        for raw in home['latestArticles']:
            raws.setdefault(raw['slug']['en'], raw)

        default_body = bodies['default']
        default_stats = bodies['stats']['default']
        for key, raw in raws.items():
            lang = languages['bySlug'].get(key, languages['default'])
            original = lang['original']
            missing = set(lang.get('missing', []))
            own = bodies['articles'].get(key, {})
            content = own.get('content', default_body)
            reads = bodies['stats']['bySlug'].get(key, default_stats)['reads']
            critic, _ = Critic.objects.get_or_create(name=raw['author']['en'])
            critic.name_i18n = raw['author']
            critic.slug_i18n = {k: writer_slug(v) for k, v in raw['author'].items()}
            critic.save(update_fields=['name_i18n', 'slug_i18n'])
            article, _ = Article.objects.update_or_create(
                slug=raw['slug'][original],
                defaults={
                    'title': raw['title'][original],
                    'category': categories[raw['categorySlug']],
                    'critic': critic,
                    'status': ArticleStatus.PUBLISHED,
                    'published_at': timezone.make_aware(
                        timezone.datetime.fromisoformat(raw['publishedAt'])
                    ),
                    'original_language': original,
                    'cover_url': own.get('coverImage', raw['image']),
                    'read_count': reads,
                    'is_featured': key in featured,
                },
            )
            article.tags.set(self._tags(raw.get('tags', [])))
            for locale in LOCALES:
                if locale in missing:
                    ArticleTranslation.objects.filter(
                        article=article, locale=locale
                    ).delete()
                    continue
                ArticleTranslation.objects.update_or_create(
                    article=article,
                    locale=locale,
                    defaults={
                        'title': raw['title'][locale],
                        'slug': raw['slug'][locale],
                        'excerpt': raw['excerpt'][locale],
                        'meta_description': own.get('metaDescription', {}).get(
                            locale, raw['excerpt'][locale]
                        ),
                        'content': content.get(locale),
                        'is_ai_generated': locale != original
                        and locale in lang.get('ai', []),
                    },
                )
        return len(raws)

    def _tags(self, raw_tags):
        tags = []
        for raw in raw_tags:
            tag, _ = Tag.objects.update_or_create(
                slug=raw['slug']['en'],
                defaults={'url_slug': raw['slug'], 'name': raw['name']},
            )
            tags.append(tag)
        return tags

    def _writers(self, writers, categories):
        for raw in writers:
            critic, _ = Critic.objects.get_or_create(name=raw['name']['en'])
            critic.name_i18n = raw['name']
            critic.bio_i18n = raw['bio']
            critic.bio = raw['bio']['en']
            critic.slug_i18n = {
                locale: writer_slug(name) for locale, name in raw['name'].items()
            }
            critic.photo_url = raw.get('photo', '')
            critic.main_category = categories.get(raw['mainCategory'])
            critic.save()
        # Every article author gets a localized name/slug even without a profile.
        for critic in Critic.objects.filter(name_i18n={}):
            critic.name_i18n = {locale: critic.name for locale in LOCALES}
            critic.slug_i18n = {locale: writer_slug(critic.name) for locale in LOCALES}
            critic.save()

    def _about(self, about):
        page = AboutPage.objects.first() or AboutPage()
        page.content = {
            'eyebrow': about['eyebrow'],
            'title': about['title'],
            'hero_image': about['heroImage'],
            'hero_alt': about['heroAlt'],
            'sections': about['sections'],
            'gallery': about['gallery'],
            'values': about['values'],
        }
        page.save()

    def _ads(self, ads):
        for raw in ads:
            Ad.objects.update_or_create(
                name=raw['name'],
                defaults={
                    'type': raw['type'],
                    'url': raw['url'],
                    'internal': raw['internal'],
                    'locales': raw['locales'],
                    'starts_at': date.fromisoformat(raw['startsAt']),
                    'ends_at': date.fromisoformat(raw['endsAt']),
                    'weight': raw['weight'],
                    'alt': raw['alt'],
                    'images': raw['images'],
                },
            )


def writer_slug(name):
    """Same rule as the frontend's writerSlug: lower-case, drop punctuation, hyphenate."""
    cleaned = re.sub(r'[^\w\s-]', '', name.strip().lower())
    return re.sub(r'\s+', '-', cleaned)
