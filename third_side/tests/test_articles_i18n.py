from django.utils import timezone
from rest_framework.test import APITestCase

from third_side.models import (
    Article,
    ArticleTranslation,
    Category,
    Critic,
    NavGroup,
    Tag,
)
from third_side.models.Article import ArticleStatus
from third_side.services.translations import sync_translations


def lexical(text):
    return {'root': {'type': 'root', 'children': [{'type': 'text', 'text': text}]}}


class ArticleI18nTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        group = NavGroup.objects.create(
            slug='visual', url_slug={'ar': 'فنون-مرئية', 'en': 'visual-arts'}
        )
        cls.cinema = Category.objects.create(
            name='Cinema',
            slug='cinema',
            group=group,
            name_i18n={'ar': 'السينما', 'en': 'Cinema'},
            url_slug={'ar': 'سينما', 'en': 'cinema'},
        )
        cls.theater = Category.objects.create(name='Theater', slug='theater')
        cls.critic = Critic.objects.create(name='Sara')
        cls.tag = Tag.objects.create(
            slug='directors', name={'ar': 'مخرجون', 'en': 'Directors'}
        )
        cls.article = Article.objects.create(
            title='شاهين',
            slug='شاهين',
            category=cls.cinema,
            critic=cls.critic,
            status=ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
            original_language='ar',
            content='نص',
        )
        cls.article.tags.add(cls.tag)
        ArticleTranslation.objects.create(
            article=cls.article,
            locale='en',
            title='Chahine',
            slug='chahine',
            excerpt='ex',
            content=lexical('hello'),
            is_ai_generated=True,
        )
        cls.other = Article.objects.create(
            title='Other',
            slug='other',
            category=cls.theater,
            critic=cls.critic,
            status=ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_by_slug_finds_any_locale_and_returns_localized_detail(self):
        for slug in ('chahine', 'شاهين'):
            response = self.client.get(f'/third_side/articles/by-slug/{slug}?lang=en')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['title'], 'Chahine')
            self.assertEqual(response.data['content_locale'], 'en')
            self.assertEqual(response.data['body'], lexical('hello'))
            self.assertEqual(response.data['slugs'], {'ar': 'شاهين', 'en': 'chahine'})

    def test_languages_original_ai_and_missing(self):
        data = self.client.get('/third_side/articles/by-slug/chahine?lang=en').data
        self.assertEqual(
            data['languages'],
            {
                'original': 'ar',
                'available': [
                    {'locale': 'ar', 'ai': False},
                    {'locale': 'en', 'ai': True},
                ],
                'missing': ['ro'],
            },
        )

    def test_missing_locale_falls_back_to_original(self):
        data = self.client.get('/third_side/articles/by-slug/chahine?lang=ro').data
        self.assertEqual(data['content_locale'], 'ar')
        self.assertEqual(data['title'], 'شاهين')

    def test_unknown_slug_404(self):
        self.assertEqual(
            self.client.get('/third_side/articles/by-slug/nope').status_code, 404
        )

    def test_list_filters(self):
        base = '/third_side/articles'
        self.assertEqual(self.client.get(f'{base}?category=cinema').data['count'], 1)
        self.assertEqual(self.client.get(f'{base}?group=visual').data['count'], 1)
        self.assertEqual(self.client.get(f'{base}?tag=directors').data['count'], 1)
        self.assertEqual(self.client.get(f'{base}?search=Chahine').data['count'], 1)

    def test_similar_prefers_same_category_and_excludes_self(self):
        data = self.client.get(f'/third_side/articles/{self.article.pk}/similar').data
        self.assertEqual([a['id'] for a in data['results']], [self.other.pk])

    def test_read_increments(self):
        url = f'/third_side/articles/{self.article.pk}/read'
        self.assertEqual(self.client.post(url).data['read_count'], 1)
        self.assertEqual(self.client.post(url).data['read_count'], 2)

    def test_categories_localized_with_group_and_slugs(self):
        data = self.client.get('/third_side/categories?lang=ar').data['results']
        cinema = next(c for c in data if c['slug'] == 'cinema')
        self.assertEqual(cinema['name'], 'السينما')
        self.assertEqual(cinema['group'], 'visual')
        self.assertEqual(cinema['url_slugs']['en'], 'cinema')

    def test_nav_groups(self):
        data = self.client.get('/third_side/nav-groups?lang=en').data['results']
        self.assertEqual(data[0]['url_slug'], 'visual-arts')
        self.assertEqual(data[0]['categories'], ['cinema'])


class TranslationSaveTests(APITestCase):
    """sync_translations: how an editor doc becomes ArticleTranslation rows."""

    def make_article(self, key):
        category = Category.objects.create(name=f'C{key}', slug=f'c{key}')
        critic = Critic.objects.create(name=f'K{key}')
        return Article.objects.create(
            title='t', slug=f't{key}', category=category, critic=critic
        )

    def test_upserts_translations(self):
        article = self.make_article('1')
        sync_translations(
            article,
            {
                'title': {'ar': 'عنوان', 'en': 'Title'},
                'slug': {'ar': 'عنوان', 'en': 'title'},
                'content': {'ar': lexical('ar'), 'en': lexical('en')},
            },
        )
        rows = {t.locale: t for t in article.translations.all()}
        self.assertEqual(set(rows), {'ar', 'en'})
        self.assertEqual(rows['en'].slug, 'title')
        self.assertEqual(rows['en'].content, lexical('en'))

    def test_copies_ai_flag_and_keeps_it_when_absent(self):
        article = self.make_article('2')

        def save(**extra):
            sync_translations(
                article,
                {
                    'title': {'ar': 'عنوان', 'en': 'Title'},
                    'slug': {'ar': 'عنوان-2', 'en': 'title-2'},
                    'content': {'ar': lexical('ar'), 'en': lexical('en')},
                    **extra,
                },
            )

        def flags():
            return {t.locale: t.is_ai_generated for t in article.translations.all()}

        save(aiGenerated={'ar': False, 'en': True})
        self.assertEqual(flags(), {'ar': False, 'en': True})
        # A doc without the field must not clear the flag.
        save()
        self.assertEqual(flags(), {'ar': False, 'en': True})
        # A human review unticks it.
        save(aiGenerated={'ar': False, 'en': False})
        self.assertEqual(flags(), {'ar': False, 'en': False})

    def test_sets_original_language_from_tick(self):
        article = self.make_article('3')

        def save(**extra):
            sync_translations(
                article,
                {
                    'title': {'ar': 'عنوان', 'en': 'Title', 'ro': 'Titlu'},
                    'slug': {'ar': 'عنوان-3', 'en': 'title-3', 'ro': 'titlu-3'},
                    'content': {'ar': lexical('ar'), 'en': lexical('en')},
                    **extra,
                },
            )
            article.refresh_from_db()
            return article.original_language

        self.assertEqual(article.original_language, 'ar')
        self.assertEqual(save(isOriginalLanguage={'en': True}), 'en')
        # No field: unchanged.
        self.assertEqual(save(), 'en')
        # Nothing ticked: unchanged.
        self.assertEqual(save(isOriginalLanguage={'ar': False}), 'en')
        # Several ticked: keep the current one if still ticked.
        self.assertEqual(save(isOriginalLanguage={'ar': True, 'en': True}), 'en')
        # Several ticked and the current one is not among them: first in order.
        self.assertEqual(save(isOriginalLanguage={'ar': True, 'ro': True}), 'ar')
        # A language without text cannot be the original.
        self.assertEqual(
            save(
                isOriginalLanguage={'ro': True},
                title={'ar': 'عنوان'},
                slug={'ar': 'عنوان-3'},
            ),
            'ar',
        )

    def test_public_read_uses_saved_translations(self):
        article = self.make_article('4')
        article.status = ArticleStatus.PUBLISHED
        article.save()
        sync_translations(
            article,
            {
                'title': {'ar': 'عنوان', 'en': 'Title'},
                'slug': {'ar': 'عنوان-4', 'en': 'title-4'},
                'content': {'ar': lexical('ar'), 'en': lexical('en')},
            },
        )
        data = self.client.get('/third_side/articles/by-slug/title-4?lang=en').data
        self.assertEqual(data['body'], lexical('en'))
        self.assertEqual(data['languages']['missing'], ['ro'])
