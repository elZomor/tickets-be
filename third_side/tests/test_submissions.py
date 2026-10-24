from django.core.cache import cache
from rest_framework.test import APITestCase

from third_side.models import Article, Category, Critic, NavGroup, ThirdSideUser
from third_side.models.Article import ArticleStatus

User = ThirdSideUser
BODY = 'x' * 120


class SubmissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        group = NavGroup.objects.create(
            slug='visual', label={'ar': 'فنون', 'en': 'Visual'}
        )
        cls.category = Category.objects.create(
            name='Cinema',
            slug='cinema',
            group=group,
            name_i18n={'ar': 'سينما', 'en': 'Cinema'},
        )
        cls.user = User.objects.create_user('u@example.com', 'pw-12345678', name='Ali', email_verified=True)
        cls.other = User.objects.create_user('o@example.com', 'pw-12345678', email_verified=True)

    def setUp(self):
        cache.clear()  # throttle counters live in the cache

    def payload(self, **kwargs):
        data = dict(
            category_slug='cinema',
            title='My piece',
            language='en',
            content=BODY,
            allow_translation=False,
        )
        data.update(kwargs)
        return data

    def post(self, **kwargs):
        return self.client.post(
            '/third_side/submissions', self.payload(**kwargs), format='json'
        )

    def test_requires_login(self):
        self.assertEqual(self.post().status_code, 401)
        self.assertEqual(
            self.client.get('/third_side/submissions/mine').status_code, 401
        )

    def test_create_is_pending_and_hidden_from_public(self):
        self.client.force_authenticate(self.user)
        response = self.post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['group_id'], 'visual')
        self.assertEqual(response.data['language'], 'en')
        self.assertFalse(response.data['allow_translation'])
        article = Article.objects.get(pk=response.data['id'])
        self.assertEqual(article.status, ArticleStatus.SUBMITTED)
        self.assertEqual(article.created_by, self.user)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/third_side/articles').data['count'], 0)

    def test_validation(self):
        self.client.force_authenticate(self.user)
        for bad in (
            {'content': 'short'},
            {'title': 'ab'},
            {'category_slug': 'nope'},
            {'language': 'fr'},
        ):
            self.assertEqual(self.post(**bad).status_code, 400, bad)

    def test_mine_lists_only_own_with_status_mapping(self):
        self.client.force_authenticate(self.user)
        ids = [self.post(title=f'Piece {i}').data['id'] for i in range(3)]
        Article.objects.filter(pk=ids[0]).update(status=ArticleStatus.PUBLISHED)
        Article.objects.filter(pk=ids[1]).update(status=ArticleStatus.REJECTED)
        self.client.force_authenticate(self.other)
        self.post(title='Not mine')
        self.client.force_authenticate(self.user)
        data = self.client.get('/third_side/submissions/mine?lang=ar').data
        self.assertEqual(data['count'], 3)
        by_id = {s['id']: s for s in data['results']}
        self.assertEqual(by_id[ids[0]]['status'], 'published')
        self.assertEqual(by_id[ids[1]]['status'], 'rejected')
        self.assertEqual(by_id[ids[2]]['status'], 'pending')
        self.assertEqual(by_id[ids[2]]['category_name'], 'سينما')
        self.assertEqual(by_id[ids[2]]['group_name'], 'فنون')
        published = by_id[ids[0]]
        self.assertEqual(published['slug'], Article.objects.get(pk=ids[0]).slug)
        self.assertEqual(published['category_url_slug'], 'cinema')
        self.assertEqual(published['group_url_slug'], 'visual')

    def test_mine_includes_articles_attached_to_the_writer_profile(self):
        self.client.force_authenticate(self.user)
        sent = self.post().data['id']
        critic = Critic.objects.get(user=self.user)
        attached = Article.objects.create(
            title='By editor', slug='by-editor', category=self.category, critic=critic
        )  # no created_by: added by an editor
        other = Article.objects.create(
            title='Other',
            slug='other',
            category=self.category,
            critic=Critic.objects.create(name='Z'),
        )
        ids = {
            s['id']
            for s in self.client.get('/third_side/submissions/mine').data['results']
        }
        self.assertEqual(ids, {sent, attached.pk})
        self.assertNotIn(other.pk, ids)

    def test_writer_profile_hidden_until_published(self):
        self.client.force_authenticate(self.user)
        article_id = self.post().data['id']
        critic = Critic.objects.get(user=self.user)
        self.assertEqual(critic.name, 'Ali')
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/third_side/critics').data['count'], 0)
        Article.objects.filter(pk=article_id).update(status=ArticleStatus.PUBLISHED)
        self.assertEqual(self.client.get('/third_side/critics').data['count'], 1)

    def test_same_title_gets_unique_slugs(self):
        self.client.force_authenticate(self.user)
        a, b = self.post().data['id'], self.post().data['id']
        self.assertNotEqual(
            Article.objects.get(pk=a).slug, Article.objects.get(pk=b).slug
        )
