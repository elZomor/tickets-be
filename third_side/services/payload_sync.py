import logging

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from third_side.models.SyncedArticle import PayloadSyncStatus, SyncedArticle

logger = logging.getLogger(__name__)

# Payload's own review workflow once an article has been pushed to it.
# Approved/rejected map back onto the Django-side status.
PAYLOAD_STATUS_READY_FOR_REVIEW = 'ready_for_review'
PAYLOAD_STATUS_APPROVED = 'approved'
PAYLOAD_STATUS_REJECTED = 'rejected'


def _payload_headers():
    return {'Authorization': f'users API-Key {settings.PAYLOAD_API_KEY}'}


def _text_node(text):
    return {
        'mode': 'normal',
        'text': text,
        'type': 'text',
        'style': '',
        'detail': 0,
        'format': 0,
        'version': 1,
    }


def _paragraph_node(text):
    return {
        'type': 'paragraph',
        'format': '',
        'indent': 0,
        'version': 1,
        'children': [_text_node(text)] if text else [],
        'direction': None,
        'textStyle': '',
        'textFormat': 0,
    }


def text_to_lexical(text):
    """Wrap a plain-text Article.content into Payload's Lexical richText JSON.

    A single paragraph holding the whole string, matching the shape
    Payload's editor itself produces (see an existing synced article's
    data.content for the full node vocabulary — this only needs the
    plain-paragraph subset).
    """
    return {
        'root': {
            'type': 'root',
            'format': '',
            'indent': 0,
            'version': 1,
            'children': [_paragraph_node(text or '')],
            'direction': None,
        }
    }


def create_payload_article(article):
    """Create the article in Payload and return its created doc."""
    resp = requests.post(
        f'{settings.PAYLOAD_API_URL}/api/articles',
        json={
            'title': article.title,
            'slug': article.slug,
            'content': text_to_lexical(article.content),
            'status': PAYLOAD_STATUS_READY_FOR_REVIEW,
        },
        headers=_payload_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get('doc', body)


def queue_payload_sync(article):
    """Record that `article` must be pushed to Payload, then queue the push.

    The SyncedArticle row is created first (status pending), so the intent
    survives Payload or the broker being down: the retry task and the
    sweeper both work from these rows. Idempotent.
    """
    synced, _ = SyncedArticle.objects.get_or_create(
        article=article, defaults={'sync_status': PayloadSyncStatus.PENDING}
    )
    if synced.sync_status == PayloadSyncStatus.SYNCED:
        return synced
    if synced.sync_status == PayloadSyncStatus.FAILED:
        synced.sync_status = PayloadSyncStatus.PENDING
        synced.save(update_fields=['sync_status', 'updated_at'])
    enqueue_push(synced.pk)
    return synced


def enqueue_push(synced_id):
    """Queue the push once the surrounding transaction commits.

    A broker outage must not break the save; the sweeper picks the row up.
    """
    from third_side.tasks import push_article_to_payload

    def send():
        try:
            push_article_to_payload.delay(synced_id)
        except Exception:
            logger.exception('Could not queue the Payload push for synced article %s', synced_id)

    transaction.on_commit(send)


def push_to_payload(synced):
    """Create the Payload doc for a pending SyncedArticle. Raises if Payload fails."""
    if synced.payload_id:
        synced.sync_status = PayloadSyncStatus.SYNCED
        synced.save(update_fields=['sync_status', 'updated_at'])
        return synced

    doc = create_payload_article(synced.article)
    with transaction.atomic():
        # Payload's webhook can land before we get here and create an
        # unlinked row for the same doc; fold it into this one.
        SyncedArticle.objects.filter(payload_id=str(doc['id'])).exclude(pk=synced.pk).delete()
        synced.payload_id = str(doc['id'])
        synced.data = doc
        synced.sync_status = PayloadSyncStatus.SYNCED
        synced.sync_error = ''
        synced.save()
    return synced


def record_failure(synced, exc, *, final=False):
    synced.sync_attempts += 1
    synced.sync_error = f'{type(exc).__name__}: {exc}'[:2000]
    synced.last_attempt_at = timezone.now()
    synced.sync_status = PayloadSyncStatus.FAILED if final else PayloadSyncStatus.PENDING
    synced.save(
        update_fields=['sync_attempts', 'sync_error', 'last_attempt_at', 'sync_status', 'updated_at']
    )
