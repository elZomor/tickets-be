from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from third_side.models import (
    Article,
    Category,
    Comment,
    Critic,
    ExpoPushDevice,
    Follow,
    Rating,
    SavedArticle,
    ThirdSideUser,
)
from third_side.models.Article import ArticleStatus

User = ThirdSideUser
URL = '/third_side/profile/me'
PASSWORD = 'pw-12345678'


class AccountDeletionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='C', slug='c')
        cls.critic = Critic.objects.create(name='K')
        cls.user = User.objects.create_user('reader@example.com', PASSWORD)
        cls.other = User.objects.create_user('other@example.com', PASSWORD)
        cls.published = cls.article('pub', ArticleStatus.PUBLISHED, cls.user)
        cls.draft = cls.article('draft', ArticleStatus.SUBMITTED, cls.user)
        cls.editing = cls.article('editing', ArticleStatus.READY_FOR_EDITING, cls.user)
        cls.theirs = cls.article('theirs', ArticleStatus.SUBMITTED, cls.other)

    @classmethod
    def article(cls, slug, status, user):
        return Article.objects.create(
            title=slug,
            slug=slug,
            category=cls.category,
            critic=cls.critic,
            status=status,
            created_by=user,
            via_website=True,
        )

    def delete(self, body=None):
        self.client.force_authenticate(self.user)
        return self.client.delete(URL, body or {'password': PASSWORD}, format='json')

    def test_account_and_personal_data_are_removed(self):
        Comment.objects.create(user=self.user, article=self.published, text='hi')
        Rating.objects.create(user=self.user, article=self.published, value=4)
        SavedArticle.objects.create(user=self.user, article=self.published)
        Follow.objects.create(
            user=self.user, target_type='critic', target_id=self.critic.pk
        )
        ExpoPushDevice.objects.create(user=self.user, token='ExponentPushToken[x]')

        response = self.delete()

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Comment.objects.exists())
        self.assertFalse(Rating.objects.exists())
        self.assertFalse(SavedArticle.objects.exists())
        self.assertFalse(Follow.objects.exists())
        self.assertFalse(ExpoPushDevice.objects.exists())
        self.assertTrue(User.objects.filter(pk=self.other.pk).exists())

    def test_published_work_stays_and_unfinished_submissions_go(self):
        self.delete()

        self.published.refresh_from_db()
        self.assertIsNone(self.published.created_by)
        self.editing.refresh_from_db()
        self.assertIsNone(self.editing.created_by)
        self.assertFalse(Article.objects.filter(pk=self.draft.pk).exists())
        self.assertTrue(Article.objects.filter(pk=self.theirs.pk).exists())

    def test_wrong_password_changes_nothing(self):
        response = self.delete({'password': 'nope'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.json())
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(Article.objects.filter(pk=self.draft.pk).exists())

    def test_password_is_required(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(URL, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_needs_login(self):
        response = self.client.delete(URL, {'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_staff_accounts_are_refused(self):
        self.user.groups.add(Group.objects.create(name='some-role'))
        response = self.delete()
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_old_tokens_stop_working(self):
        login = self.client.post(
            '/third_side/auth/login',
            {'email': 'reader@example.com', 'password': PASSWORD},
            format='json',
        )
        auth = f"Bearer {login.json()['access']}"
        deleted = self.client.delete(
            URL, {'password': PASSWORD}, format='json', HTTP_AUTHORIZATION=auth
        )
        self.assertEqual(deleted.status_code, 204)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL, HTTP_AUTHORIZATION=auth).status_code, 401)
