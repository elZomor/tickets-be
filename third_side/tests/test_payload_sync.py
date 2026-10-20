from unittest import mock

import requests
from celery.exceptions import Retry
from django.test import TestCase, override_settings
from django.utils import timezone

from third_side.models import Article, ArticleStatus, Category, Critic, SyncedArticle
from third_side.models.SyncedArticle import PayloadSyncStatus
from third_side.tasks import MAX_RETRIES, push_article_to_payload, sweep_payload_syncs

PAYLOAD = 'third_side.services.payload_sync.create_payload_article'


def make_article(status=ArticleStatus.DRAFT):
    category, _ = Category.objects.get_or_create(slug='c', defaults={'name': 'C'})
    critic = Critic.objects.create(name='K')
    return Article.objects.create(
        title='t',
        slug=f't{Article.objects.count()}',
        category=category,
        critic=critic,
        status=status,
    )


@override_settings(PAYLOAD_API_URL='http://payload', PAYLOAD_API_KEY='k')
class PayloadPushTests(TestCase):
    def move_to_ready(self, article):
        with mock.patch('third_side.tasks.push_article_to_payload.delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                article.status = ArticleStatus.READY_FOR_EDITING
                article.save()
        return delay

    def test_transition_records_pending_row_and_queues_push(self):
        article = make_article()
        delay = self.move_to_ready(article)
        synced = SyncedArticle.objects.get(article=article)
        self.assertEqual(synced.sync_status, PayloadSyncStatus.PENDING)
        self.assertIsNone(synced.payload_id)
        delay.assert_called_once_with(synced.pk)

    def test_save_while_already_ready_does_not_queue_again(self):
        article = make_article()
        self.move_to_ready(article)
        delay = self.move_to_ready(article)
        delay.assert_not_called()

    def test_broker_down_does_not_break_the_save(self):
        article = make_article()
        with mock.patch(
            'third_side.tasks.push_article_to_payload.delay',
            side_effect=OSError('redis down'),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                article.status = ArticleStatus.READY_FOR_EDITING
                article.save()
        self.assertEqual(
            SyncedArticle.objects.get(article=article).sync_status,
            PayloadSyncStatus.PENDING,
        )

    def test_task_syncs_row(self):
        article = make_article(ArticleStatus.READY_FOR_EDITING)
        synced = SyncedArticle.objects.get(article=article)
        with mock.patch(PAYLOAD, return_value={'id': 77}):
            push_article_to_payload.apply(args=[synced.pk]).get()
        synced.refresh_from_db()
        self.assertEqual(
            (synced.payload_id, synced.sync_status), ('77', PayloadSyncStatus.SYNCED)
        )

    def test_task_failure_keeps_pending_and_retries(self):
        article = make_article(ArticleStatus.READY_FOR_EDITING)
        synced = SyncedArticle.objects.get(article=article)
        with (
            mock.patch(PAYLOAD, side_effect=requests.ConnectionError('down')),
            mock.patch.object(
                push_article_to_payload, 'retry', side_effect=Retry()
            ) as retry,
        ):
            push_article_to_payload.apply(args=[synced.pk])
        retry.assert_called_once()
        synced.refresh_from_db()
        self.assertEqual(synced.sync_status, PayloadSyncStatus.PENDING)
        self.assertEqual(synced.sync_attempts, 1)
        self.assertIn('down', synced.sync_error)

    def test_last_retry_marks_failed(self):
        article = make_article(ArticleStatus.READY_FOR_EDITING)
        synced = SyncedArticle.objects.get(article=article)
        with mock.patch(PAYLOAD, side_effect=requests.ConnectionError('down')):
            push_article_to_payload.apply(args=[synced.pk], retries=MAX_RETRIES)
        synced.refresh_from_db()
        self.assertEqual(synced.sync_status, PayloadSyncStatus.FAILED)

    def test_webhook_row_for_same_doc_is_folded_in(self):
        article = make_article(ArticleStatus.READY_FOR_EDITING)
        synced = SyncedArticle.objects.get(article=article)
        SyncedArticle.objects.create(
            payload_id='5', data={'id': 5}
        )  # webhook won the race
        with mock.patch(PAYLOAD, return_value={'id': 5}):
            push_article_to_payload.apply(args=[synced.pk]).get()
        self.assertEqual(SyncedArticle.objects.filter(payload_id='5').count(), 1)
        self.assertEqual(SyncedArticle.objects.get(payload_id='5').article, article)

    def test_sweeper_requeues_idle_rows_and_creates_missing_ones(self):
        stuck = make_article(ArticleStatus.READY_FOR_EDITING)
        row = SyncedArticle.objects.get(article=stuck)
        row.sync_status = PayloadSyncStatus.FAILED
        row.save()
        recent = make_article(ArticleStatus.READY_FOR_EDITING)
        SyncedArticle.objects.filter(article=recent).update(
            last_attempt_at=timezone.now()
        )
        orphan = make_article(ArticleStatus.READY_FOR_EDITING)
        SyncedArticle.objects.filter(article=orphan).delete()
        with mock.patch('third_side.tasks.push_article_to_payload.delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                sweep_payload_syncs()
        queued = {call.args[0] for call in delay.call_args_list}
        self.assertEqual(
            queued,
            {row.pk, SyncedArticle.objects.get(article=orphan).pk},
        )
        row.refresh_from_db()
        self.assertEqual(row.sync_status, PayloadSyncStatus.PENDING)
