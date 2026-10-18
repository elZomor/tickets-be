import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from third_side.models import Article, ArticleStatus
from third_side.models.SyncedArticle import PayloadSyncStatus, SyncedArticle
from third_side.services.payload_sync import (
    enqueue_push,
    push_to_payload,
    record_failure,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 8
MAX_BACKOFF_SECONDS = 30 * 60
# The sweeper leaves a row alone while a retry is likely still scheduled.
SWEEP_MIN_AGE = timedelta(minutes=10)


@shared_task(bind=True, max_retries=MAX_RETRIES)
def push_article_to_payload(self, synced_id):
    """Create an article's Payload doc, retrying with backoff while Payload is down."""
    synced = SyncedArticle.objects.select_related('article').filter(pk=synced_id).first()
    if synced is None or synced.article is None or synced.sync_status == PayloadSyncStatus.SYNCED:
        return
    try:
        push_to_payload(synced)
    except Exception as exc:
        final = self.request.retries >= self.max_retries
        record_failure(synced, exc, final=final)
        if final:
            logger.error(
                'Giving up pushing article %s to Payload after %s attempts: %s',
                synced.article_id,
                synced.sync_attempts,
                exc,
            )
            return
        logger.warning('Payload push for article %s failed, retrying: %s', synced.article_id, exc)
        raise self.retry(exc=exc, countdown=min(30 * 2**self.request.retries, MAX_BACKOFF_SECONDS))


@shared_task
def sweep_payload_syncs():
    """Safety net for pushes the retry chain lost or gave up on.

    Re-queues pending/failed rows that have been idle a while, and creates
    the missing row for READY_FOR_EDITING articles that never got one
    (articles moved before this existed, or a signal that failed outright).
    """
    from third_side.services.payload_sync import queue_payload_sync

    for article in Article.objects.filter(
        status=ArticleStatus.READY_FOR_EDITING, synced_article__isnull=True
    ):
        queue_payload_sync(article)

    cutoff = timezone.now() - SWEEP_MIN_AGE
    stale = SyncedArticle.objects.exclude(sync_status=PayloadSyncStatus.SYNCED).filter(
        article__isnull=False
    )
    queued = 0
    for synced in stale:
        if synced.last_attempt_at and synced.last_attempt_at > cutoff:
            continue
        if synced.sync_status == PayloadSyncStatus.FAILED:
            synced.sync_status = PayloadSyncStatus.PENDING
            synced.save(update_fields=['sync_status', 'updated_at'])
        enqueue_push(synced.pk)
        queued += 1
    return queued
