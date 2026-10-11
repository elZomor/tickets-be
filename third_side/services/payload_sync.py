import requests
from django.conf import settings

from third_side.models.SyncedArticle import SyncedArticle

# Payload's own review workflow once an article has been pushed to it.
# Approved/rejected map back onto the Django-side status.
PAYLOAD_STATUS_READY_FOR_REVIEW = 'ready_for_review'
PAYLOAD_STATUS_APPROVED = 'approved'
PAYLOAD_STATUS_REJECTED = 'rejected'


def _payload_headers():
    return {'Authorization': f'users API-Key {settings.PAYLOAD_API_KEY}'}


def create_payload_article(article):
    """Create the article in Payload and return its created doc."""
    resp = requests.post(
        f'{settings.PAYLOAD_API_URL}/api/articles',
        json={
            'title': article.title,
            'slug': article.slug,
            'content': article.content,
            'status': PAYLOAD_STATUS_READY_FOR_REVIEW,
        },
        headers=_payload_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get('doc', body)


def ensure_synced_article(article):
    """Create the Payload article + linking SyncedArticle row, if not already done.

    Idempotent: a second call for an article that already has a
    synced_article is a no-op.
    """
    existing = SyncedArticle.objects.filter(article=article).first()
    if existing:
        return existing

    doc = create_payload_article(article)
    return SyncedArticle.objects.create(
        payload_id=str(doc['id']),
        data=doc,
        article=article,
    )
