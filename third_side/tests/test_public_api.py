from third_side.models import ThirdSideUser
from rest_framework.test import APITestCase

from third_side.models import Article, Category, Critic
from third_side.models.Article import ArticleStatus

User = ThirdSideUser


class PublicArticleApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Cinema', slug='cinema')
        cls.critic = Critic.objects.create(name='Critic')
        for i, status in enumerate(
            [ArticleStatus.PUBLISHED, ArticleStatus.PUBLISHED, ArticleStatus.DRAFT]
        ):
            Article.objects.create(
                title=f'A{i}',
                slug=f'a{i}',
                category=cls.category,
                critic=cls.critic,
                status=status,
            )

    def test_anonymous_sees_only_published(self):
        response = self.client.get('/third_side/articles')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

    def test_list_is_paginated_envelope(self):
        response = self.client.get('/third_side/articles')
        for key in (
            'count',
            'total_pages',
            'current_page',
            'next',
            'previous',
            'results',
        ):
            self.assertIn(key, response.data)

    def test_categories_public(self):
        response = self.client.get('/third_side/categories')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['slug'], 'cinema')

    def test_write_requires_auth(self):
        response = self.client.post('/third_side/articles', {})
        self.assertEqual(response.status_code, 401)
