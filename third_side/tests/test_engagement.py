from rest_framework.test import APITestCase

from third_side.models import Article, Category, Comment, Critic, ThirdSideUser
from third_side.models.Article import ArticleStatus

User = ThirdSideUser


class EngagementTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name='C', slug='c')
        critic = Critic.objects.create(name='K')
        cls.article = Article.objects.create(
            title='t',
            slug='t',
            category=category,
            critic=critic,
            status=ArticleStatus.PUBLISHED,
        )
        cls.other = Article.objects.create(
            title='o',
            slug='o',
            category=category,
            critic=critic,
            status=ArticleStatus.PUBLISHED,
        )
        cls.alice = User.objects.create_user(
            'alice@example.com', 'pw-12345678', name='Alice'
        )
        cls.bob = User.objects.create_user('bob@example.com', 'pw-12345678')

    def login(self, user):
        self.client.force_authenticate(user)

    def test_comment_create_returns_author_and_counts(self):
        self.login(self.alice)
        response = self.client.post(
            '/third_side/comments',
            {'article': self.article.pk, 'text': '  hello  '},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['author_name'], 'Alice')
        self.assertEqual(response.data['text'], 'hello')
        self.assertEqual(response.data['likes_count'], 0)
        self.assertFalse(response.data['liked_by_me'])

    def test_comment_validation(self):
        self.login(self.alice)
        for text in ('   ', 'x' * 2001):
            response = self.client.post(
                '/third_side/comments',
                {'article': self.article.pk, 'text': text},
                format='json',
            )
            self.assertEqual(response.status_code, 400, text[:5])

    def test_list_filters_by_article_newest_first(self):
        Comment.objects.create(user=self.alice, article=self.article, text='a')
        Comment.objects.create(user=self.alice, article=self.article, text='b')
        Comment.objects.create(user=self.alice, article=self.other, text='c')
        data = self.client.get(f'/third_side/comments?article={self.article.pk}').data
        self.assertEqual([c['text'] for c in data['results']], ['b', 'a'])

    def test_like_unlike_idempotent_and_liked_by_me(self):
        comment = Comment.objects.create(
            user=self.alice, article=self.article, text='a'
        )
        url = f'/third_side/comments/{comment.pk}/like'
        self.assertEqual(self.client.post(url).status_code, 401)
        self.login(self.bob)
        for _ in range(2):
            data = self.client.post(url).data
            self.assertEqual(data['likes_count'], 1)
            self.assertTrue(data['liked_by_me'])
        listed = self.client.get(f'/third_side/comments?article={self.article.pk}')
        self.assertTrue(listed.data['results'][0]['liked_by_me'])
        data = self.client.delete(url).data
        self.assertEqual(data['likes_count'], 0)
        self.assertFalse(data['liked_by_me'])

    def test_ratings_are_private_and_upsert(self):
        self.login(self.alice)
        r = self.client.post(
            '/third_side/ratings',
            {'article': self.article.pk, 'value': 4},
            format='json',
        )
        self.assertEqual(r.status_code, 201)
        r = self.client.post(
            '/third_side/ratings',
            {'article': self.article.pk, 'value': 2},
            format='json',
        )
        self.assertEqual(r.status_code, 200)
        mine = self.client.get(f'/third_side/ratings?article={self.article.pk}').data
        self.assertEqual([x['value'] for x in mine['results']], [2])
        self.login(self.bob)
        self.assertEqual(self.client.get('/third_side/ratings').data['count'], 0)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/third_side/ratings').status_code, 401)

    def test_article_rating_summary(self):
        from third_side.models import ArticleTranslation

        # Joined translations must not inflate the rating count.
        for locale in ('ar', 'en'):
            ArticleTranslation.objects.create(
                article=self.article, locale=locale, title='t', slug=f't-{locale}'
            )
        for user, value in ((self.alice, 5), (self.bob, 3)):
            self.login(user)
            self.client.post(
                '/third_side/ratings',
                {'article': self.article.pk, 'value': value},
                format='json',
            )
        self.client.force_authenticate(None)
        data = self.client.get('/third_side/articles/by-slug/t').data
        self.assertEqual(data['rating'], {'average': 4.0, 'count': 2})

    def test_report_is_idempotent_per_reader(self):
        self.login(self.alice)
        body = {'content_type': 'article', 'object_id': self.article.pk}
        self.assertEqual(
            self.client.post('/third_side/reports', body, format='json').status_code,
            201,
        )
        self.assertEqual(
            self.client.post('/third_side/reports', body, format='json').status_code,
            200,
        )

    def test_read_counter_throttled_scope_exists(self):
        from django.conf import settings

        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        self.assertIn('third_side_write', rates)
        self.assertIn('third_side_read', rates)
