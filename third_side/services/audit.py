"""Activity log: what an editor changed, who did it, before and after.

Views call `snapshot()` around a write and `record()` with the two snapshots.
A snapshot is a flat, JSON-safe dict of the editable fields; media files appear
as storage keys (never signed URLs) so the same file never looks "changed".
"""

from datetime import date, datetime
from decimal import Decimal

from django.db.models.fields.files import FieldFile

from third_side.models import (
    AboutPage,
    ActivityLog,
    Article,
    ArticleTranslation,
    Category,
    Critic,
    FestivalPost,
    Media,
    NavGroup,
    Report,
    SiteSettings,
    Tag,
)
from third_side.models.ActivityLog import ActivityAction, ActivityObject

OBJECT_TYPES = {
    Article: ActivityObject.ARTICLE,
    FestivalPost: ActivityObject.FESTIVAL_POST,
    Category: ActivityObject.CATEGORY,
    Critic: ActivityObject.CRITIC,
    Media: ActivityObject.MEDIA,
    Tag: ActivityObject.TAG,
    Report: ActivityObject.REPORT,
    NavGroup: ActivityObject.NAV_GROUP,
    AboutPage: ActivityObject.ABOUT,
    SiteSettings: ActivityObject.SITE_SETTINGS,
}

# Bookkeeping and counters: they change without an editor doing anything.
SKIP_FIELDS = {'id', 'created_at', 'updated_at', 'read_count', 'share_count'}

EMPTY = (None, '', [], {})


def _plain(value):
    if isinstance(value, FieldFile):
        return value.name or ''
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _article_extras(article):
    # order_by() builds a fresh query, so prefetched (stale) rows are not used.
    data = {'tags': list(article.tags.order_by('slug').values_list('slug', flat=True))}
    for row in ArticleTranslation.objects.filter(article=article).order_by('locale'):
        for field in (
            'title',
            'slug',
            'excerpt',
            'seo_title',
            'meta_description',
            'content',
            'is_ai_generated',
        ):
            data[f'{field}.{row.locale}'] = _plain(getattr(row, field))
    return data


def _festival_post_extras(post):
    return {
        'media': [
            {
                'image': _plain(item.image) or item.image_url,
                'alt_i18n': item.alt_i18n,
                'order': item.order,
            }
            for item in post.media.order_by('order', 'id')
        ]
    }


_EXTRAS = {Article: _article_extras, FestivalPost: _festival_post_extras}


def snapshot(instance):
    """Flat dict of the instance's tracked fields."""
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in SKIP_FIELDS:
            continue
        data[field.name] = _plain(getattr(instance, field.attname))
    extras = _EXTRAS.get(type(instance))
    if extras and instance.pk:
        data.update(extras(instance))
    return data


def diff(before, after):
    """{field: {before, after}} for the fields whose value differs."""
    return {
        key: {'before': before.get(key), 'after': after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


def _whole(values, side):
    """Changes for a create (side='after') or a delete (side='before')."""
    other = 'before' if side == 'after' else 'after'
    return {
        key: {side: value, other: None}
        for key, value in sorted(values.items())
        if value not in EMPTY
    }


def object_repr(instance):
    for name in ('title', 'name', 'label'):
        text = getattr(instance, name, '')
        if isinstance(text, dict):  # a per-language name (tags)
            text = text.get('en') or next((v for v in text.values() if v), '')
        if text:
            return str(text)[:255]
    return f'{type(instance).__name__} #{instance.pk}'[:255]


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = forwarded.split(',')[0].strip() if forwarded else None
    return ip or request.META.get('REMOTE_ADDR') or None


def write(request, action, object_type, object_id, repr_, changes):
    """Store one log row. `changes` empty means nothing happened: no row."""
    if not changes:
        return None
    user = getattr(request, 'user', None)
    signed_in = bool(getattr(user, 'pk', None))
    return ActivityLog.objects.create(
        actor=user if signed_in else None,
        actor_name=user.display_name if signed_in else '',
        actor_email=user.email if signed_in else '',
        action=action,
        object_type=object_type,
        object_id=object_id,
        object_repr=repr_,
        changes=changes,
        ip_address=client_ip(request),
    )


def record(request, action, instance, before, after, pk=None, repr_=None):
    """Log a create / update / delete of `instance` from its two snapshots.

    A deleted instance has lost its pk, so a delete passes `pk` and `repr_`
    taken before the delete.
    """
    if action == ActivityAction.CREATE:
        changes = _whole(after, 'after')
    elif action == ActivityAction.DELETE:
        changes = _whole(before, 'before')
    else:
        changes = diff(before, after)
    return write(
        request,
        action,
        OBJECT_TYPES[type(instance)],
        pk if pk is not None else instance.pk,
        repr_ if repr_ is not None else object_repr(instance),
        changes,
    )
