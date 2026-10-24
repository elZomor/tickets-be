"""Web Push delivery of inbox notifications.

Copy is trilingual and follows the recipient's `language`. The push is only a
nudge: the inbox row is the record, so every failure here is logged and
swallowed.
"""

import json
import logging

import requests
from django.conf import settings
from django.utils import timezone

from third_side.i18n import localize

from third_side.models import ExpoPushDevice, NotificationPreference, PushSubscription
from third_side.models.Notification import NotificationType as T
from third_side.services.notify import (
    NOTIFICATIONS_SEGMENT,
    PREFERENCE_OF,
    PROFILE_SEGMENT,
    account_paths,
)

logger = logging.getLogger(__name__)

MAX_FAILURES = 5
TTL_SECONDS = 24 * 60 * 60

COPY = {
    'ar': {
        'site': 'الضلع الثالث',
        'status': {
            'under_review': 'قيد المراجعة',
            'changes_requested': 'مطلوب تعديلات',
            'ready_for_editing': 'جاهز للتحرير',
            'ready_for_publishing': 'جاهز للنشر',
            'scheduled': 'مجدول',
            'published': 'منشور',
            'archived': 'مؤرشف',
            'rejected': 'مرفوض',
        },
        T.ARTICLE_STATUS: 'تغيّرت حالة مقالك «{title}»: {status}',
        T.PROFILE_UPDATED: 'تم تحديث بيانات حسابك',
        T.REPORT_REVIEWED: 'راجع فريق الإشراف بلاغك',
        T.CONTENT_REPORTED: 'تم الإبلاغ عن {target}',
        'target_article': 'مقالك «{title}»',
        'target_comment': 'تعليقك على «{title}»',
        T.ARTICLE_COMMENT: '{name} علّق على «{title}»',
        T.ARTICLE_COMMENT + '_many': '{count} تعليقات جديدة على «{title}»',
        T.ARTICLE_RATING: 'تقييم جديد ({value}/5) على «{title}»',
        T.ARTICLE_RATING + '_many': '{count} تقييمات جديدة على «{title}»',
        T.NEW_ARTICLE: 'مقال جديد: «{title}»',
        T.NEW_ARTICLE + '_by': 'مقال جديد من {critic}: «{title}»',
        T.NEW_FESTIVAL_POST: 'جديد في {festival}',
    },
    'en': {
        'site': 'Third Side',
        'status': {
            'under_review': 'under review',
            'changes_requested': 'changes requested',
            'ready_for_editing': 'ready for editing',
            'ready_for_publishing': 'ready for publishing',
            'scheduled': 'scheduled',
            'published': 'published',
            'archived': 'archived',
            'rejected': 'rejected',
        },
        T.ARTICLE_STATUS: 'Your article “{title}” is now {status}',
        T.PROFILE_UPDATED: 'Your account details were updated',
        T.REPORT_REVIEWED: 'Our moderators reviewed your report',
        T.CONTENT_REPORTED: '{target} was reported',
        'target_article': 'your article “{title}”',
        'target_comment': 'your comment on “{title}”',
        T.ARTICLE_COMMENT: '{name} commented on “{title}”',
        T.ARTICLE_COMMENT + '_many': '{count} new comments on “{title}”',
        T.ARTICLE_RATING: 'New rating ({value}/5) on “{title}”',
        T.ARTICLE_RATING + '_many': '{count} new ratings on “{title}”',
        T.NEW_ARTICLE: 'New article: “{title}”',
        T.NEW_ARTICLE + '_by': 'New article by {critic}: “{title}”',
        T.NEW_FESTIVAL_POST: 'New in {festival}',
    },
    'ro': {
        'site': 'Third Side',
        'status': {
            'under_review': 'în revizuire',
            'changes_requested': 'se cer modificări',
            'ready_for_editing': 'gata de editare',
            'ready_for_publishing': 'gata de publicare',
            'scheduled': 'programat',
            'published': 'publicat',
            'archived': 'arhivat',
            'rejected': 'respins',
        },
        T.ARTICLE_STATUS: 'Articolul tău „{title}” este acum {status}',
        T.PROFILE_UPDATED: 'Datele contului tău au fost actualizate',
        T.REPORT_REVIEWED: 'Moderatorii ți-au verificat raportarea',
        T.CONTENT_REPORTED: '{target} a fost raportat',
        'target_article': 'articolul tău „{title}”',
        'target_comment': 'comentariul tău la „{title}”',
        T.ARTICLE_COMMENT: '{name} a comentat „{title}”',
        T.ARTICLE_COMMENT + '_many': '{count} comentarii noi la „{title}”',
        T.ARTICLE_RATING: 'Evaluare nouă ({value}/5) pentru „{title}”',
        T.ARTICLE_RATING + '_many': '{count} evaluări noi pentru „{title}”',
        T.NEW_ARTICLE: 'Articol nou: „{title}”',
        T.NEW_ARTICLE + '_by': 'Articol nou de {critic}: „{title}”',
        T.NEW_FESTIVAL_POST: 'Nou la {festival}',
    },
}


def render(notification, lang):
    """{title, body, url, tag} of a notification in `lang`."""
    copy = COPY[lang]
    params = notification.params or {}
    kind = notification.type
    count = notification.count

    if kind == T.ARTICLE_STATUS:
        body = copy[kind].format(
            title=params.get('title', ''),
            status=copy['status'].get(params.get('status'), params.get('status', '')),
        )
    elif kind == T.CONTENT_REPORTED:
        target = copy['target_' + params.get('target', 'article')].format(
            title=params.get('title', '')
        )
        body = copy[kind].format(target=target)
    elif kind in (T.ARTICLE_COMMENT, T.ARTICLE_RATING):
        key = kind + '_many' if count > 1 else kind
        body = copy[key].format(
            name=params.get('name', ''),
            title=params.get('title', ''),
            value=params.get('value', ''),
            count=count,
        )
    elif kind == T.NEW_ARTICLE:
        key = kind + '_by' if params.get('critic') else kind
        body = copy[key].format(
            title=params.get('title', ''), critic=params.get('critic', '')
        )
    elif kind == T.NEW_FESTIVAL_POST:
        name = localize(params.get('festival_names'), lang, params.get('festival', ''))
        body = copy[kind].format(festival=name)
    else:
        body = copy[kind]

    paths = params.get('paths') or account_paths(NOTIFICATIONS_SEGMENT)
    if kind == T.PROFILE_UPDATED:
        paths = account_paths(PROFILE_SEGMENT)
    return {
        'title': copy['site'],
        'body': body,
        'url': paths.get(lang) or paths.get('ar'),
        'tag': notification.dedupe_key,
        'type': kind,
    }


def wants_push(user, kind):
    preference = NotificationPreference.objects.filter(user=user).first()
    if preference is None:
        return True  # defaults are all on
    return preference.push_enabled and getattr(preference, PREFERENCE_OF[kind])


def send_to_user(user, notification):
    """Push `notification` to every device of `user` that wants it: browsers
    (Web Push) and phones (Expo)."""
    if not settings.THIRD_SIDE_SEND_PUSH:
        return 0
    if not wants_push(user, notification.type):
        return 0
    message = render(notification, user.language)
    sent = 0
    if settings.VAPID_PRIVATE_KEY:
        payload = json.dumps(message, ensure_ascii=False)
        for subscription in PushSubscription.objects.filter(user=user):
            sent += _send(subscription, payload)
    sent += _send_expo(user, message)
    return sent


def _send(subscription, payload):
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            # pywebpush writes `aud` into the claims, so give it a fresh dict.
            vapid_claims={'sub': settings.VAPID_SUBJECT},
            ttl=TTL_SECONDS,
            headers={'Urgency': 'normal'},
            timeout=10,
        )
    except WebPushException as error:
        status = getattr(error.response, 'status_code', None)
        if status in (404, 410):
            subscription.delete()
        else:
            _fail(subscription, error)
        return 0
    except Exception as error:  # noqa: BLE001 - one dead device must not stop the rest
        _fail(subscription, error)
        return 0
    subscription.last_success_at = timezone.now()
    subscription.failure_count = 0
    subscription.save(update_fields=['last_success_at', 'failure_count'])
    return 1


def _fail(subscription, error):
    logger.warning('Push failed for subscription %s: %s', subscription.pk, error)
    subscription.failure_count += 1
    if subscription.failure_count >= MAX_FAILURES:
        subscription.delete()
    else:
        subscription.save(update_fields=['failure_count'])


def _send_expo(user, message):
    """One request to Expo's push service for all of the user's phones. The
    app maps `url` (a web path) to its own screen."""
    devices = list(ExpoPushDevice.objects.filter(user=user))
    if not devices:
        return 0
    messages = [
        {
            'to': device.token,
            'title': message['title'],
            'body': message['body'],
            'data': {
                'url': message['url'],
                'type': message['type'],
                'tag': message['tag'],
            },
            'sound': 'default',
            'ttl': TTL_SECONDS,
            'channelId': 'default',
        }
        for device in devices
    ]
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    if settings.EXPO_PUSH_ACCESS_TOKEN:
        headers['Authorization'] = f'Bearer {settings.EXPO_PUSH_ACCESS_TOKEN}'
    try:
        response = requests.post(
            settings.EXPO_PUSH_URL, json=messages, headers=headers, timeout=10
        )
        response.raise_for_status()
        tickets = response.json().get('data', [])
    except Exception as error:  # noqa: BLE001 - the inbox row is the record
        logger.warning('Expo push request failed: %s', error)
        for device in devices:
            _fail_expo(device, error)
        return 0

    sent = 0
    for device, ticket in zip(devices, tickets):
        if ticket.get('status') == 'ok':
            device.last_success_at = timezone.now()
            device.failure_count = 0
            device.save(update_fields=['last_success_at', 'failure_count'])
            sent += 1
        elif (ticket.get('details') or {}).get('error') == 'DeviceNotRegistered':
            device.delete()
        else:
            _fail_expo(device, ticket.get('message', 'rejected'))
    return sent


def _fail_expo(device, error):
    logger.warning('Expo push failed for device %s: %s', device.pk, error)
    device.failure_count += 1
    if device.failure_count >= MAX_FAILURES:
        device.delete()
    else:
        device.save(update_fields=['failure_count'])
