from datetime import timedelta
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from pywebpush import WebPushException
from rest_framework.test import APITestCase

from third_side import tasks
from third_side.models import (
    Article,
    Category,
    Comment,
    Critic,
    FestivalPost,
    Festival,
    Follow,
    NavGroup,
    Notification,
    NotificationPreference,
    PushSubscription,
    Rating,
    Report,
    ThirdSideUser,
)
from third_side.models.Article import ArticleStatus
from third_side.models.Follow import FollowTarget
from third_side.models.Notification import NotificationType
from third_side.services.publishing import promote_due_articles

User = ThirdSideUser
BASE = '/third_side'


@override_settings(THIRD_SIDE_NOTIFY_EAGER=True)
class NotificationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = NavGroup.objects.create(slug='g')
        cls.category = Category.objects.create(name='C', slug='c', group=cls.group)
        cls.critic = Critic.objects.create(name='K')
        cls.author = User.objects.create_user(
            'author@example.com', 'pw-12345678', name='Author', language='en'
        )
        cls.other = User.objects.create_user(
            'other@example.com', 'pw-12345678', name='Other', language='ar'
        )
        cls.article = Article.objects.create(
            title='Title',
            slug='title',
            category=cls.category,
            critic=cls.critic,
            status=ArticleStatus.PUBLISHED,
            created_by=cls.author,
        )

    def setUp(self):
        cache.clear()

    def inbox(self, user, **filters):
        return Notification.objects.filter(recipient=user, **filters)

    def test_comment_notifies_author_and_coalesces(self):
        with self.captureOnCommitCallbacks(execute=True):
            Comment.objects.create(user=self.other, article=self.article, text='a')
        row = self.inbox(self.author, type=NotificationType.ARTICLE_COMMENT).get()
        self.assertEqual(row.count, 1)
        self.assertEqual(row.params['article_id'], self.article.pk)
        self.assertEqual(row.params['paths']['en'], '/en/g/c/title')
        with self.captureOnCommitCallbacks(execute=True):
            Comment.objects.create(user=self.other, article=self.article, text='b')
        row.refresh_from_db()
        self.assertEqual(row.count, 2)
        self.assertEqual(self.inbox(self.author).count(), 1)

    def test_read_row_is_reopened_by_new_comment(self):
        with self.captureOnCommitCallbacks(execute=True):
            Comment.objects.create(user=self.other, article=self.article, text='a')
        Notification.objects.update(read_at=timezone.now())
        with self.captureOnCommitCallbacks(execute=True):
            Comment.objects.create(user=self.other, article=self.article, text='b')
        row = self.inbox(self.author).get()
        self.assertIsNone(row.read_at)
        self.assertEqual(row.count, 1)

    def test_no_self_notification(self):
        with self.captureOnCommitCallbacks(execute=True):
            Comment.objects.create(user=self.author, article=self.article, text='me')
            Rating.objects.create(user=self.author, article=self.article, value=5)
        self.assertEqual(Notification.objects.count(), 0)

    def test_hidden_comment_is_skipped(self):
        with self.captureOnCommitCallbacks(execute=True):
            Comment.objects.create(
                user=self.other, article=self.article, text='x', is_hidden=True
            )
        self.assertEqual(Notification.objects.count(), 0)

    def test_rating_notifies_author(self):
        with self.captureOnCommitCallbacks(execute=True):
            Rating.objects.create(user=self.other, article=self.article, value=4)
        row = self.inbox(self.author, type=NotificationType.ARTICLE_RATING).get()
        self.assertEqual(row.params['value'], 4)

    def test_report_tells_author_without_naming_reporter(self):
        content_type = ContentType.objects.get_for_model(Article)
        with self.captureOnCommitCallbacks(execute=True):
            Report.objects.create(
                reporter=self.other,
                content_type=content_type,
                object_id=self.article.pk,
                reason='spam',
            )
        row = self.inbox(self.author, type=NotificationType.CONTENT_REPORTED).get()
        self.assertEqual(row.params['target'], 'article')
        self.assertNotIn(str(self.other.pk), str(row.params))
        self.assertNotIn(self.other.email, str(row.params))

    def test_reviewed_report_tells_reporter_once(self):
        content_type = ContentType.objects.get_for_model(Article)
        report = Report.objects.create(
            reporter=self.other,
            content_type=content_type,
            object_id=self.article.pk,
        )
        report.reviewed_at = timezone.now()
        with self.captureOnCommitCallbacks(execute=True):
            report.save(update_fields=['reviewed_at'])
            report.save(update_fields=['reviewed_at'])
        self.assertEqual(
            self.inbox(self.other, type=NotificationType.REPORT_REVIEWED).count(), 1
        )

    def test_status_change_notifies_author(self):
        article = Article.objects.create(
            title='D',
            slug='d',
            category=self.category,
            critic=self.critic,
            status=ArticleStatus.SUBMITTED,
            created_by=self.author,
        )
        with self.captureOnCommitCallbacks(execute=True):
            article.status = ArticleStatus.CHANGES_REQUESTED
            article.save()
        row = self.inbox(self.author, type=NotificationType.ARTICLE_STATUS).get()
        self.assertEqual(row.params['status'], ArticleStatus.CHANGES_REQUESTED)

    def test_author_own_moves_are_not_notified(self):
        article = Article.objects.create(
            title='D',
            slug='d',
            category=self.category,
            critic=self.critic,
            status=ArticleStatus.DRAFT,
            created_by=self.author,
        )
        with self.captureOnCommitCallbacks(execute=True):
            article.status = ArticleStatus.SUBMITTED
            article.save()
        self.assertEqual(Notification.objects.count(), 0)

    def test_publish_tells_followers_of_each_target_once(self):
        follower_critic = User.objects.create_user('a@example.com', 'pw-12345678')
        follower_category = User.objects.create_user('b@example.com', 'pw-12345678')
        follower_group = User.objects.create_user('c@example.com', 'pw-12345678')
        both = User.objects.create_user('d@example.com', 'pw-12345678')
        bystander = User.objects.create_user('e@example.com', 'pw-12345678')
        for user, kind, target in [
            (follower_critic, FollowTarget.CRITIC, self.critic.pk),
            (follower_category, FollowTarget.CATEGORY, self.category.pk),
            (follower_group, FollowTarget.NAVGROUP, self.group.pk),
            (both, FollowTarget.CRITIC, self.critic.pk),
            (both, FollowTarget.CATEGORY, self.category.pk),
        ]:
            Follow.objects.create(user=user, target_type=kind, target_id=target)
        draft = Article.objects.create(
            title='N',
            slug='n',
            category=self.category,
            critic=self.critic,
            status=ArticleStatus.READY_FOR_PUBLISHING,
            created_by=self.author,
        )
        with self.captureOnCommitCallbacks(execute=True):
            draft.status = ArticleStatus.PUBLISHED
            draft.save()
            draft.save()
        rows = Notification.objects.filter(type=NotificationType.NEW_ARTICLE)
        self.assertEqual(
            set(rows.values_list('recipient_id', flat=True)),
            {follower_critic.pk, follower_category.pk, follower_group.pk, both.pk},
        )
        self.assertEqual(rows.count(), 4)
        self.assertFalse(rows.filter(recipient=bystander).exists())

    def test_scheduled_promotion_notifies_once(self):
        follower = User.objects.create_user('f@example.com', 'pw-12345678')
        Follow.objects.create(
            user=follower, target_type=FollowTarget.CRITIC, target_id=self.critic.pk
        )
        Article.objects.create(
            title='S',
            slug='s',
            category=self.category,
            critic=self.critic,
            status=ArticleStatus.SCHEDULED,
            published_at=timezone.now() - timedelta(minutes=1),
            created_by=self.author,
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(promote_due_articles(), 1)
            self.assertEqual(promote_due_articles(), 0)
        self.assertEqual(
            self.inbox(follower, type=NotificationType.NEW_ARTICLE).count(), 1
        )
        self.assertEqual(
            self.inbox(self.author, type=NotificationType.ARTICLE_STATUS).count(), 1
        )

    def test_festival_post_notifies_followers(self):
        festival = Festival.objects.create(
            slug='fest',
            name_i18n={'ar': 'مهرجان', 'en': 'Fest'},
            starts_on=timezone.now().date(),
            ends_on=timezone.now().date(),
        )
        Follow.objects.create(
            user=self.other, target_type=FollowTarget.FESTIVAL, target_id=festival.pk
        )
        with self.captureOnCommitCallbacks(execute=True):
            FestivalPost.objects.create(
                festival=festival, type='text', body_i18n={'ar': 'x'}
            )
        row = self.inbox(self.other, type=NotificationType.NEW_FESTIVAL_POST).get()
        self.assertEqual(row.params['paths']['en'], '/en/festivals/fest')

    def test_inactive_user_gets_nothing(self):
        self.author.is_active = False
        self.author.save()
        with self.captureOnCommitCallbacks(execute=True):
            Comment.objects.create(user=self.other, article=self.article, text='a')
        self.assertEqual(Notification.objects.count(), 0)


PUSH = dict(
    THIRD_SIDE_NOTIFY_EAGER=True,
    THIRD_SIDE_SEND_PUSH=True,
    VAPID_PRIVATE_KEY='private',
)


@override_settings(**PUSH)
class PushTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name='C', slug='c')
        critic = Critic.objects.create(name='K')
        cls.author = User.objects.create_user(
            'author@example.com', 'pw-12345678', language='en'
        )
        cls.other = User.objects.create_user('other@example.com', 'pw-12345678')
        cls.article = Article.objects.create(
            title='Title',
            slug='title',
            category=category,
            critic=critic,
            status=ArticleStatus.PUBLISHED,
            created_by=cls.author,
        )
        PushSubscription.objects.create(
            user=cls.author, endpoint='https://push.example/1', p256dh='k', auth='a'
        )

    def comment(self):
        with self.captureOnCommitCallbacks(execute=True):
            Comment.objects.create(user=self.other, article=self.article, text='a')

    @mock.patch('pywebpush.webpush')
    def test_push_is_sent_in_the_users_language(self, webpush):
        self.comment()
        self.assertEqual(webpush.call_count, 1)
        payload = webpush.call_args.kwargs['data']
        self.assertIn('commented on', payload)
        self.assertIn('/en/c/title', payload)
        subscription = PushSubscription.objects.get()
        self.assertIsNotNone(subscription.last_success_at)

    @mock.patch('pywebpush.webpush')
    def test_preference_off_keeps_inbox_but_skips_push(self, webpush):
        NotificationPreference.objects.create(user=self.author, activity=False)
        self.comment()
        webpush.assert_not_called()
        self.assertEqual(Notification.objects.filter(recipient=self.author).count(), 1)

    @mock.patch('pywebpush.webpush')
    def test_gone_endpoint_is_removed(self, webpush):
        webpush.side_effect = WebPushException(
            'gone', response=mock.Mock(status_code=410)
        )
        self.comment()
        self.assertFalse(PushSubscription.objects.exists())
        self.assertEqual(Notification.objects.count(), 1)

    @mock.patch('pywebpush.webpush')
    def test_other_failures_count_then_drop(self, webpush):
        webpush.side_effect = RuntimeError('boom')
        for index in range(5):
            self.comment()
            Notification.objects.all().delete()
        self.assertFalse(PushSubscription.objects.exists())

    @override_settings(THIRD_SIDE_SEND_PUSH=False)
    @mock.patch('pywebpush.webpush')
    def test_kill_switch(self, webpush):
        self.comment()
        webpush.assert_not_called()


class PurgeTests(APITestCase):
    def test_old_read_rows_are_purged(self):
        user = User.objects.create_user('u@example.com', 'pw-12345678')
        old = Notification.objects.create(
            recipient=user,
            type=NotificationType.PROFILE_UPDATED,
            dedupe_key='a',
            read_at=timezone.now() - timedelta(days=100),
        )
        unread = Notification.objects.create(
            recipient=user, type=NotificationType.PROFILE_UPDATED, dedupe_key='b'
        )
        tasks.purge_notifications()
        self.assertFalse(Notification.objects.filter(pk=old.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=unread.pk).exists())
