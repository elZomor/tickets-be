from django.core.cache import cache
from rest_framework.test import APITestCase

from third_side.models import (
    Article,
    Category,
    Critic,
    Festival,
    FestivalPost,
    Role,
    ThirdSideUser,
)
from third_side.models.Article import ArticleStatus

URL = '/third_side/festival-posts'


class FestivalPostAdminTests(APITestCase):
    """The admin panel's festival-post write API and editor-only reads."""

    @classmethod
    def setUpTestData(cls):
        cls.festival = Festival.objects.create(
            slug='fest',
            name_i18n={'en': 'Fest'},
            starts_on='2026-01-01',
            ends_on='2026-01-05',
        )
        category = Category.objects.create(name='C', slug='c')
        critic = Critic.objects.create(name='K')
        cls.article = Article.objects.create(
            title='Art',
            slug='art',
            category=category,
            critic=critic,
            status=ArticleStatus.PUBLISHED,
        )
        cls.draft_article = Article.objects.create(
            title='Draft',
            slug='draft',
            category=category,
            critic=critic,
            status=ArticleStatus.DRAFT,
        )
        cls.editor = ThirdSideUser.objects.create_user(
            'e@example.com', 'pw', role=Role.EDITOR
        )
        cls.reader = ThirdSideUser.objects.create_user(
            'r@example.com', 'pw', role=Role.READER
        )

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.editor)

    def body(self, **extra):
        return {
            'festival': self.festival.pk,
            'type': 'text',
            'body_i18n': {'en': 'Hello', 'ar': 'مرحبا'},
            **extra,
        }

    def create(self, **extra):
        return self.client.post(URL, self.body(**extra), format='json')

    def test_creates_every_type(self):
        cases = {
            'text': {},
            'titled_text': {'title_i18n': {'en': 'T'}},
            'image': {'media': [{'image_url': 'http://x/a.png', 'alt_i18n': {}}]},
            'image_caption': {
                'media': [{'image_url': 'http://x/a.png'}],
                'caption_i18n': {'en': 'C'},
            },
            'video': {'video_url': 'https://youtu.be/abc'},
            'video_caption': {
                'video_url': 'https://youtu.be/abc',
                'caption_i18n': {'en': 'C'},
            },
            'article': {'article': self.article.pk},
        }
        for kind, extra in cases.items():
            response = self.create(type=kind, **extra)
            self.assertEqual(response.status_code, 201, (kind, response.data))
        self.assertEqual(FestivalPost.objects.count(), 7)

    def test_type_rules(self):
        self.assertEqual(self.create(type='titled_text').status_code, 400)
        self.assertEqual(self.create(type='text', body_i18n={}).status_code, 400)
        self.assertEqual(self.create(type='video').status_code, 400)
        self.assertEqual(self.create(type='article').status_code, 400)
        self.assertEqual(self.create(type='image').status_code, 400)

    def test_unknown_language_is_rejected(self):
        self.assertEqual(self.create(body_i18n={'fr': 'Bonjour'}).status_code, 400)

    def test_switching_type_clears_fields_that_no_longer_apply(self):
        post = self.create(
            type='titled_text', title_i18n={'en': 'T'}, body_i18n={'en': 'B'}
        ).data
        response = self.client.patch(
            f"{URL}/{post['id']}",
            {'type': 'video', 'video_url': 'https://youtu.be/abc'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        saved = FestivalPost.objects.get(pk=post['id'])
        self.assertEqual((saved.title_i18n, saved.body_i18n), ({}, {}))
        self.assertEqual(saved.video_url, 'https://youtu.be/abc')

    def test_update_replaces_media(self):
        post = self.create(
            type='image',
            media=[{'image_url': 'http://x/1.png'}, {'image_url': 'http://x/2.png'}],
        ).data
        response = self.client.patch(
            f"{URL}/{post['id']}",
            {'media': [{'image_url': 'http://x/3.png', 'alt_i18n': {'en': 'three'}}]},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        urls = list(
            FestivalPost.objects.get(pk=post['id']).media.values_list(
                'image_url', flat=True
            )
        )
        self.assertEqual(urls, ['http://x/3.png'])

    def test_doc_returns_the_form_shape(self):
        post = self.create(type='article', article=self.article.pk, body_i18n={}).data
        data = self.client.get(f"{URL}/{post['id']}/doc").data
        self.assertEqual(data['festival'], self.festival.pk)
        self.assertEqual(data['article'], self.article.pk)
        self.assertEqual(data['article_title'], 'Art')
        self.assertEqual(data['media'], [])

    def test_editors_see_unpublished_but_the_public_does_not(self):
        self.create(is_published=False)
        self.create(type='article', article=self.draft_article.pk, body_i18n={})
        self.create()
        editor_list = self.client.get(URL).data['results']
        self.assertEqual(len(editor_list), 3)
        self.assertEqual(
            sorted(p['is_published'] for p in editor_list), [False, True, True]
        )
        self.client.force_authenticate(None)
        public = self.client.get(URL).data['results']
        self.assertEqual(len(public), 1)

    def test_list_exposes_locales(self):
        self.create()
        post = self.client.get(f'{URL}?lang=en').data['results'][0]
        self.assertEqual(post['locales'], ['ar', 'en'])

    def test_delete(self):
        post = self.create().data
        self.assertEqual(self.client.delete(f"{URL}/{post['id']}").status_code, 204)
        self.assertFalse(FestivalPost.objects.exists())

    def test_only_editors_can_write_or_read_docs(self):
        post = self.create().data
        for user in (None, self.reader):
            self.client.force_authenticate(user)
            expected = (401, 403) if user is None else (403,)
            self.assertIn(
                self.client.post(URL, self.body(), format='json').status_code, expected
            )
            self.assertIn(
                self.client.patch(f"{URL}/{post['id']}", {}, format='json').status_code,
                expected,
            )
            self.assertIn(
                self.client.delete(f"{URL}/{post['id']}").status_code, expected
            )
            self.assertIn(
                self.client.get(f"{URL}/{post['id']}/doc").status_code, expected
            )
