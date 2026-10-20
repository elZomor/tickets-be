from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from third_side.models import (
    Article,
    ArticleTranslation,
    Category,
    Critic,
    Festival,
    FestivalPost,
    FestivalPostMedia,
    NavGroup,
)
from third_side.models.Article import ArticleStatus


class FestivalApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.festival = Festival.objects.create(
            slug='book-fair',
            slug_i18n={'ar': 'معرض-الكتاب', 'en': 'book-fair', 'ro': 'targul-de-carte'},
            name_i18n={'ar': 'معرض الكتاب', 'en': 'Book Fair', 'ro': 'Targul de Carte'},
            description_i18n={'en': 'Panels and signings'},
            location_i18n={'en': 'Cairo'},
            cover_url='/mock/literature-hero.jpg',
            starts_on=date(2026, 6, 20),
            ends_on=date(2026, 7, 5),
        )
        cls.other = Festival.objects.create(
            slug='film',
            name_i18n={'en': 'Film'},
            starts_on=date(2026, 11, 1),
            ends_on=date(2026, 11, 9),
        )
        group = NavGroup.objects.create(
            slug='written', url_slug={'ar': 'مكتوب', 'en': 'written', 'ro': 'scris'}
        )
        category = Category.objects.create(
            name='Literature',
            slug='literature',
            group=group,
            url_slug={'ar': 'أدب', 'en': 'literature', 'ro': 'literatura'},
        )
        critic = Critic.objects.create(name='C')
        cls.article = Article.objects.create(
            title='The Word First',
            slug='the-word-first',
            category=category,
            critic=critic,
            status=ArticleStatus.PUBLISHED,
            original_language='en',
            cover_url='/mock/article-1.jpg',
        )
        ArticleTranslation.objects.create(
            article=cls.article,
            locale='en',
            title='The Word First',
            slug='the-word-first',
            excerpt='Excerpt en',
        )
        now = timezone.now()
        cls.text = FestivalPost.objects.create(
            festival=cls.festival,
            type='text',
            body_i18n={'ar': 'نص', 'en': 'Text'},
            published_at=now - timedelta(hours=3),
        )
        cls.titled = FestivalPost.objects.create(
            festival=cls.festival,
            type='titled_text',
            title_i18n={'en': 'Title'},
            body_i18n={'en': 'Body'},
            published_at=now - timedelta(hours=1),
        )
        cls.image = FestivalPost.objects.create(
            festival=cls.other,
            type='image_caption',
            caption_i18n={'en': 'Cap'},
            published_at=now - timedelta(hours=2),
        )
        FestivalPostMedia.objects.create(
            post=cls.image, image_url='/mock/a.jpg', alt_i18n={'en': 'Alt'}, order=1
        )
        FestivalPostMedia.objects.create(
            post=cls.image, image_url='/mock/b.jpg', alt_i18n={'en': 'Alt b'}, order=0
        )
        cls.video = FestivalPost.objects.create(
            festival=cls.other,
            type='video',
            video_url='https://youtu.be/x',
            poster_url='/mock/p.jpg',
            published_at=now - timedelta(hours=5),
        )
        cls.article_post = FestivalPost.objects.create(
            festival=cls.other,
            type='article',
            article=cls.article,
            published_at=now - timedelta(hours=4),
        )
        FestivalPost.objects.create(
            festival=cls.other,
            type='text',
            body_i18n={'en': 'hidden'},
            is_published=False,
        )

    def posts(self, query=''):
        return self.client.get(f'/third_side/festival-posts?lang=en{query}')

    def test_list_is_paginated_envelope_with_counts(self):
        response = self.client.get('/third_side/festivals?lang=en')
        self.assertEqual(response.status_code, 200)
        for key in (
            'count',
            'total_pages',
            'current_page',
            'next',
            'previous',
            'results',
        ):
            self.assertIn(key, response.data)
        by_slug = {f['slug']: f for f in response.data['results']}
        self.assertEqual(by_slug['book-fair']['posts_count'], 2)
        self.assertEqual(by_slug['film']['posts_count'], 3)  # unpublished not counted
        # newest start first
        self.assertEqual(response.data['results'][0]['slug'], 'film')

    def test_localized_fields_and_slugs(self):
        data = self.client.get('/third_side/festivals?lang=ar').data['results']
        book = next(f for f in data if f['id'] == self.festival.id)
        self.assertEqual(book['name'], 'معرض الكتاب')
        self.assertEqual(book['slug'], 'معرض-الكتاب')
        self.assertEqual(
            book['slugs'],
            {'ar': 'معرض-الكتاب', 'en': 'book-fair', 'ro': 'targul-de-carte'},
        )
        self.assertEqual(book['cover'], '/mock/literature-hero.jpg')
        self.assertEqual(book['starts_on'], '2026-06-20')

    def test_by_slug_any_locale(self):
        for slug in ('book-fair', 'معرض-الكتاب', 'targul-de-carte'):
            response = self.client.get(f'/third_side/festivals/by-slug/{slug}?lang=ro')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['id'], self.festival.id)
            self.assertEqual(response.data['name'], 'Targul de Carte')
        self.assertEqual(
            self.client.get('/third_side/festivals/by-slug/nope').status_code, 404
        )

    def test_posts_newest_first_and_hide_unpublished(self):
        data = self.posts().data
        self.assertEqual(data['count'], 5)
        self.assertEqual(
            [p['id'] for p in data['results']],
            [
                self.titled.id,
                self.image.id,
                self.text.id,
                self.article_post.id,
                self.video.id,
            ],
        )

    def test_posts_filter_and_pagination(self):
        self.assertEqual(self.posts(f'&festival={self.festival.id}').data['count'], 2)
        page = self.posts('&page_size=2').data
        self.assertEqual(len(page['results']), 2)
        self.assertIsNotNone(page['next'])
        second = self.posts('&page_size=2&page=2').data
        self.assertEqual(
            {p['id'] for p in page['results']} & {p['id'] for p in second['results']},
            set(),
        )

    def test_post_shapes_per_type(self):
        by_id = {p['id']: p for p in self.posts().data['results']}
        titled = by_id[self.titled.id]
        self.assertEqual((titled['title'], titled['body']), ('Title', 'Body'))
        self.assertNotIn('media', titled)
        self.assertEqual(titled['festival']['slug'], 'book-fair')
        image = by_id[self.image.id]
        self.assertEqual(image['caption'], 'Cap')
        self.assertEqual(
            [m['url'] for m in image['media']], ['/mock/b.jpg', '/mock/a.jpg']
        )
        self.assertEqual(image['media'][0]['alt'], 'Alt b')
        self.assertNotIn('body', image)
        video = by_id[self.video.id]
        self.assertEqual(
            video['video'],
            {'kind': 'embed', 'url': 'https://youtu.be/x', 'poster': '/mock/p.jpg'},
        )

    def test_article_block_path_and_cover(self):
        post = next(p for p in self.posts().data['results'] if p['type'] == 'article')
        self.assertEqual(
            post['article'],
            {
                'title': 'The Word First',
                'excerpt': 'Excerpt en',
                'cover': '/mock/article-1.jpg',
                'path': '/en/written/literature/the-word-first',
            },
        )
        # Not translated to ro yet: the original is shown and flagged.
        ro = self.client.get('/third_side/festival-posts?lang=ro').data['results']
        item = next(p for p in ro if p['type'] == 'article')
        self.assertEqual(item['content_locale'], 'en')
        self.assertTrue(item['article']['path'].startswith('/ro/scris/literatura/'))

    def test_hidden_article_post_is_dropped(self):
        Article.objects.filter(pk=self.article.pk).update(is_hidden=True)
        self.assertEqual(self.posts().data['count'], 4)

    def test_text_fallback_sets_content_locale(self):
        ro = self.client.get('/third_side/festival-posts?lang=ro').data['results']
        text = next(p for p in ro if p['id'] == self.text.id)
        self.assertEqual(text['body'], 'نص')
        self.assertEqual(text['content_locale'], 'ar')

    def test_read_only_for_everyone(self):
        self.assertEqual(self.client.post('/third_side/festivals', {}).status_code, 405)
        # Posts are written by editors only (see test_festival_post_admin).
        self.assertIn(
            self.client.post('/third_side/festival-posts', {}).status_code, (401, 403)
        )
