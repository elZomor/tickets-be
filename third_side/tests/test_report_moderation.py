from unittest import mock

from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APITestCase

from third_side.models import (
    Article,
    Category,
    Comment,
    Critic,
    ModerationAction,
    Report,
    ThirdSideUser,
)
from third_side.models.Article import ArticleStatus
from third_side.services.roles import sync_roles

User = ThirdSideUser
BASE = '/third_side/reports'


class ReportModerationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        sync_roles()
        category = Category.objects.create(name='C', slug='c')
        critic = Critic.objects.create(name='K')
        cls.author = User.objects.create_user(
            'author@example.com', 'pw-12345678', name='Author', language='en'
        )
        cls.article = Article.objects.create(
            title='t',
            slug='t',
            category=category,
            critic=critic,
            status=ArticleStatus.PUBLISHED,
            created_by=cls.author,
        )
        cls.commenter = User.objects.create_user(
            'commenter@example.com', 'pw-12345678', name='Commenter', language='ro'
        )
        cls.reporter = User.objects.create_user(
            'reporter@example.com', 'pw-12345678', language='ar'
        )
        cls.reporter.email_verified = True
        cls.reporter.save()
        cls.moderator = User.objects.create_user('mod@example.com', 'pw-12345678')
        cls.moderator.groups.add(Group.objects.get(name='Moderator'))

    def setUp(self):
        cache.clear()
        self.comment = Comment.objects.create(
            user=self.commenter, article=self.article, text='rude'
        )

    def report(self, user=None, **extra):
        self.client.force_authenticate(user or self.reporter)
        body = {
            'content_type': 'comment',
            'object_id': self.comment.pk,
            'reason': 'abuse_hate',
            **extra,
        }
        return self.client.post(BASE, body, format='json')

    def resolve(self, report_id, **body):
        self.client.force_authenticate(self.moderator)
        return self.client.post(f'{BASE}/{report_id}/resolve', body, format='json')

    def test_create_stores_reason_and_note(self):
        response = self.report(note='insults')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['reason'], 'abuse_hate')
        self.assertNotIn('email', str(response.data))
        self.assertEqual(Report.objects.get().note, 'insults')

    def test_bad_reason_is_refused(self):
        self.assertEqual(self.report(reason='nope').status_code, 400)

    def test_unverified_reader_cannot_report(self):
        self.commenter.email_verified = False
        self.commenter.save()
        response = self.report(user=self.commenter)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'email_not_verified')

    def test_list_needs_permission_and_filters(self):
        self.report()
        self.client.force_authenticate(self.reporter)
        self.assertEqual(self.client.get(BASE).status_code, 403)
        self.client.force_authenticate(self.moderator)
        data = self.client.get(BASE, {'reviewed': 'false'}).data
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['author']['email'], 'commenter@example.com')
        self.assertEqual(self.client.get(BASE, {'reviewed': 'true'}).data['count'], 0)
        self.assertEqual(self.client.get(BASE, {'content_type': 'article'}).data['count'], 0)

    def test_dismiss_unhides_and_settles_all_reports(self):
        first = self.report().data['id']
        other = User.objects.create_user('o@example.com', 'pw-12345678')
        other.email_verified = True
        other.save()
        self.report(user=other)
        self.comment.is_hidden = True
        self.comment.save()
        response = self.resolve(first, action='dismiss')
        self.assertEqual(response.status_code, 200)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_hidden)
        self.assertEqual(Report.objects.filter(reviewed_at__isnull=True).count(), 0)
        self.assertEqual(ModerationAction.objects.get().action, 'dismiss')

    def test_hide_keeps_content_hidden(self):
        report_id = self.report().data['id']
        self.resolve(report_id, action='hide')
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_hidden)

    def test_warn_sends_email_in_author_language_and_counts_strike(self):
        report_id = self.report().data['id']
        self.client.force_authenticate(self.moderator)
        template = self.client.get(f'{BASE}/{report_id}/warning-template').data
        self.assertEqual(template['language'], 'ro')
        with self.settings(THIRD_SIDE_SEND_EMAIL=True), mock.patch(
            'third_side.services.moderation_mail.send_email'
        ) as send:
            response = self.resolve(
                report_id,
                action='warn',
                send_email=True,
                email_subject=template['subject'],
                email_body=template['body'],
                hide_content=True,
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['email_sent'])
        recipients = [call.args[0] for call in send.call_args_list]
        self.assertEqual(recipients[0], 'commenter@example.com')
        self.assertIn('reporter@example.com', recipients)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_hidden)
        self.client.force_authenticate(self.moderator)
        detail = self.client.get(f'{BASE}/{report_id}').data
        self.assertEqual(detail['author_history']['strikes'], 1)

    def test_mail_failure_does_not_undo_decision(self):
        report_id = self.report().data['id']
        with self.settings(THIRD_SIDE_SEND_EMAIL=True), mock.patch(
            'third_side.services.moderation_mail.send_email', side_effect=Exception('x')
        ):
            response = self.resolve(
                report_id,
                action='warn',
                send_email=True,
                email_subject='s',
                email_body='b',
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['email_sent'])
        self.assertIsNotNone(Report.objects.get().reviewed_at)

    def test_warn_email_needs_subject_and_body(self):
        report_id = self.report().data['id']
        self.assertEqual(
            self.resolve(report_id, action='warn', send_email=True).status_code, 400
        )

    def test_delete_comment(self):
        report_id = self.report().data['id']
        self.assertEqual(self.resolve(report_id, action='delete').status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())
        self.assertEqual(ModerationAction.objects.get().action, 'delete')

    def test_delete_article_only_hides(self):
        self.client.force_authenticate(self.reporter)
        report_id = self.client.post(
            BASE,
            {'content_type': 'article', 'object_id': self.article.pk},
            format='json',
        ).data['id']
        self.moderator.groups.clear()
        self.moderator.is_superuser = True
        self.moderator.save()
        self.assertEqual(self.resolve(report_id, action='delete').status_code, 200)
        self.article.refresh_from_db()
        self.assertTrue(self.article.is_hidden)

    def test_suspend_deactivates_author(self):
        report_id = self.report().data['id']
        self.assertEqual(self.resolve(report_id, action='suspend').status_code, 200)
        self.commenter.refresh_from_db()
        self.assertFalse(self.commenter.is_active)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_hidden)

    def test_cannot_suspend_staff(self):
        self.commenter.groups.add(Group.objects.get(name='Writer'))
        report_id = self.report().data['id']
        self.assertEqual(self.resolve(report_id, action='suspend').status_code, 400)

    def test_resolve_needs_change_report(self):
        report_id = self.report().data['id']
        self.client.force_authenticate(self.reporter)
        response = self.client.post(
            f'{BASE}/{report_id}/resolve', {'action': 'dismiss'}, format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_review_alias_dismisses(self):
        report_id = self.report().data['id']
        self.client.force_authenticate(self.moderator)
        response = self.client.patch(f'{BASE}/{report_id}/review')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(Report.objects.get().reviewed_at)
