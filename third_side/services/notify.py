"""Create inbox notifications and hand them to the push sender.

The inbox row stores only the type and its params; copy is rendered later
(frontend dictionaries for the inbox, services/push.py for the push). Triggers
call `enqueue` from signals so the work leaves the request and survives only if
the surrounding transaction commits.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from third_side.i18n import localize
from third_side.models import Notification, ThirdSideUser
from third_side.models.Notification import NotificationType

logger = logging.getLogger(__name__)

# Which preference switch gates the push of each type.
PREFERENCE_OF = {
    NotificationType.ARTICLE_STATUS: 'status',
    NotificationType.PROFILE_UPDATED: 'profile',
    NotificationType.REPORT_REVIEWED: 'reports',
    NotificationType.CONTENT_REPORTED: 'reports',
    NotificationType.ARTICLE_COMMENT: 'activity',
    NotificationType.ARTICLE_RATING: 'activity',
    NotificationType.NEW_ARTICLE: 'follows',
    NotificationType.NEW_FESTIVAL_POST: 'follows',
}

PUSH_CHUNK = 500


def enqueue(task, *args):
    """Run `task` after the current transaction commits; never raises.

    With THIRD_SIDE_NOTIFY_EAGER the task runs inline (tests, no broker).
    """

    def run():
        try:
            if settings.THIRD_SIDE_NOTIFY_EAGER:
                task.apply(args=args, throw=True)
            else:
                task.delay(*args)
        except Exception:  # noqa: BLE001 - a notification must never break a write
            logger.exception('Could not queue %s', getattr(task, 'name', task))

    transaction.on_commit(run)


def notify(recipient_ids, type, params, dedupe_key, coalesce=False):
    """Write one inbox row per recipient and queue the push for the new ones.

    A row already holding `dedupe_key` is left alone (retries are idempotent).
    With `coalesce`, an unread row absorbs the event (count + 1) instead, and a
    read one is reopened. Returns the ids of rows that deserve a push.
    """
    wanted = {pk for pk in recipient_ids if pk}
    if not wanted:
        return []
    active = set(
        ThirdSideUser.objects.filter(pk__in=wanted, is_active=True).values_list(
            'pk', flat=True
        )
    )
    if not active:
        return []

    if coalesce:
        fresh = [_coalesce(pk, type, params, dedupe_key) for pk in active]
        ids = [pk for pk in fresh if pk]
    else:
        existing = set(
            Notification.objects.filter(
                recipient_id__in=active, dedupe_key=dedupe_key
            ).values_list('recipient_id', flat=True)
        )
        fresh = active - existing
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient_id=pk, type=type, params=params, dedupe_key=dedupe_key
                )
                for pk in fresh
            ],
            ignore_conflicts=True,
            batch_size=PUSH_CHUNK,
        )
        ids = list(
            Notification.objects.filter(
                recipient_id__in=fresh, dedupe_key=dedupe_key
            ).values_list('pk', flat=True)
        )

    from third_side.tasks import send_push

    for start in range(0, len(ids), PUSH_CHUNK):
        enqueue(send_push, ids[start : start + PUSH_CHUNK])
    return ids


def _coalesce(recipient_id, type, params, dedupe_key):
    row, created = Notification.objects.get_or_create(
        recipient_id=recipient_id,
        dedupe_key=dedupe_key,
        defaults={'type': type, 'params': params},
    )
    if created:
        return row.pk
    if row.read_at is None:
        Notification.objects.filter(pk=row.pk).update(
            count=F('count') + 1, params=params, updated_at=timezone.now()
        )
        return None
    row.read_at = None
    row.count = 1
    row.params = params
    row.save(update_fields=['read_at', 'count', 'params', 'updated_at'])
    return row.pk


# ---- addresses the frontend serves (keep in step with app/lib/accountPaths.ts)

FESTIVALS_SEGMENT = {'ar': 'مهرجانات', 'en': 'festivals', 'ro': 'festivaluri'}
NOTIFICATIONS_SEGMENT = {'ar': 'الإشعارات', 'en': 'notifications', 'ro': 'notificari'}
PROFILE_SEGMENT = {'ar': 'ملفي-الشخصي', 'en': 'profile', 'ro': 'profil'}


def account_paths(segments):
    return {lang: f'/{lang}/{segment}' for lang, segment in segments.items()}


def article_paths(article):
    """{ar, en, ro: path} of an article, for params the inbox and push link to."""
    from third_side.services.festivals import article_path, shown_translation

    return {
        lang: article_path(article, lang, shown_translation(article, lang))
        for lang in ('ar', 'en', 'ro')
    }


def festival_paths(festival):
    return {
        lang: f'/{lang}/{FESTIVALS_SEGMENT[lang]}/'
        f'{localize(festival.slug_i18n, lang, festival.slug)}'
        for lang in ('ar', 'en', 'ro')
    }
