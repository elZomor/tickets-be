"""Background work: notification fan-out, push delivery and housekeeping.

Each notify_* task takes ids (never model instances) so it can run in a worker,
and a dedupe key fixed when the event happened so a retry cannot double-send.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from third_side.models import (
    Article,
    Comment,
    Follow,
    FestivalPost,
    ModerationAction,
    Notification,
    Rating,
    Report,
)
from third_side.models.Article import ArticleStatus
from third_side.models.Follow import FollowTarget
from third_side.models.Notification import NotificationType
from third_side.services import push
from third_side.services.notify import article_paths, festival_paths, notify
from third_side.services.publishing import promote_due_articles

logger = logging.getLogger(__name__)

# Moves the author makes themselves; they do not need telling.
AUTHOR_OWN_STATUSES = (ArticleStatus.DRAFT, ArticleStatus.SUBMITTED)
READ_RETENTION_DAYS = 90


def article_author_id(article):
    """The account to tell about an article: who wrote it, else the writer's login."""
    return article.created_by_id or (
        article.critic.user_id if article.critic_id else None
    )


def _article_params(article, **extra):
    return {
        'article_id': article.pk,
        'title': article.title,
        'paths': article_paths(article),
        **extra,
    }


def _followers(*targets):
    """Ids of the users following any of the (target_type, target_id) pairs."""
    query = Q()
    for target_type, target_id in targets:
        if target_id:
            query |= Q(target_type=target_type, target_id=target_id)
    if not query:
        return set()
    return set(Follow.objects.filter(query).values_list('user_id', flat=True))


@shared_task
def notify_article_status(article_id, new_status, dedupe_key):
    article = (
        Article.objects.select_related('critic', 'category')
        .filter(pk=article_id)
        .first()
    )
    if article is None or new_status in AUTHOR_OWN_STATUSES:
        return
    notify(
        [article_author_id(article)],
        NotificationType.ARTICLE_STATUS,
        _article_params(article, status=new_status),
        dedupe_key,
    )


@shared_task
def notify_article_published(article_id):
    """Tell the followers of the writer, category and sub-category group."""
    article = (
        Article.objects.select_related('critic', 'category')
        .filter(pk=article_id)
        .first()
    )
    if article is None or article.is_hidden:
        return
    followers = _followers(
        (FollowTarget.CRITIC, article.critic_id),
        (FollowTarget.CATEGORY, article.category_id),
        (FollowTarget.NAVGROUP, article.category.group_id),
    )
    followers.discard(article_author_id(article))
    notify(
        followers,
        NotificationType.NEW_ARTICLE,
        _article_params(
            article, critic=article.critic.name if article.critic_id else ''
        ),
        f'article:{article.pk}:published',
    )


@shared_task
def notify_comment(comment_id):
    comment = (
        Comment.objects.select_related('user', 'article__critic', 'article__category')
        .filter(pk=comment_id)
        .first()
    )
    if comment is None or comment.is_hidden:
        return
    author_id = article_author_id(comment.article)
    if author_id == comment.user_id:
        return
    notify(
        [author_id],
        NotificationType.ARTICLE_COMMENT,
        _article_params(comment.article, name=comment.user.display_name),
        f'comment:{comment.article_id}',
        coalesce=True,
    )


@shared_task
def notify_rating(rating_id):
    rating = (
        Rating.objects.select_related('article__critic', 'article__category')
        .filter(pk=rating_id)
        .first()
    )
    if rating is None:
        return
    author_id = article_author_id(rating.article)
    if author_id == rating.user_id:
        return
    notify(
        [author_id],
        NotificationType.ARTICLE_RATING,
        _article_params(rating.article, value=rating.value),
        f'rating:{rating.article_id}',
        coalesce=True,
    )


def _report_target(report):
    """(kind, article, author_id) of a reported article or comment."""
    target = report.target
    if target is None:
        return None, None, None
    if report.content_type.model == 'comment':
        return 'comment', target.article, target.user_id
    return 'article', target, article_author_id(target)


@shared_task
def notify_content_reported(report_id):
    """Tell the author. The reporter is never named."""
    report = Report.objects.select_related('content_type').filter(pk=report_id).first()
    if report is None:
        return
    kind, article, author_id = _report_target(report)
    if article is None:
        return
    notify(
        [author_id],
        NotificationType.CONTENT_REPORTED,
        _article_params(article, target=kind),
        f'reported:{report.content_type_id}:{report.object_id}',
        coalesce=True,
    )


@shared_task
def notify_report_reviewed(report_id):
    report = Report.objects.select_related('content_type').filter(pk=report_id).first()
    if report is None or report.reviewed_at is None:
        return
    decision = (
        ModerationAction.objects.filter(
            content_type=report.content_type, object_id=report.object_id
        )
        .order_by('-id')
        .first()
    )
    kind, article, _ = _report_target(report)
    params = {
        'target': kind or report.content_type.model,
        'outcome': (
            'dismissed' if decision and decision.action == 'dismiss' else 'actioned'
        ),
    }
    if article is not None:
        params['title'] = article.title
        params['paths'] = article_paths(article)
    notify(
        [report.reporter_id],
        NotificationType.REPORT_REVIEWED,
        params,
        f'report:{report.pk}:reviewed',
    )


@shared_task
def notify_profile_updated(user_id, fields):
    notify(
        [user_id],
        NotificationType.PROFILE_UPDATED,
        {'fields': sorted(fields)},
        'profile',
        coalesce=True,
    )


@shared_task
def notify_festival_post(post_id):
    post = FestivalPost.objects.select_related('festival').filter(pk=post_id).first()
    if post is None or not post.is_published or post.published_at > timezone.now():
        return
    festival = post.festival
    notify(
        _followers((FollowTarget.FESTIVAL, festival.pk)),
        NotificationType.NEW_FESTIVAL_POST,
        {
            'festival': festival.name_i18n.get('ar')
            or next(iter(festival.name_i18n.values()), festival.slug),
            'festival_names': festival.name_i18n,
            'post_id': post.pk,
            'paths': festival_paths(festival),
        },
        f'festival_post:{post.pk}',
    )


@shared_task
def send_push(notification_ids):
    rows = Notification.objects.filter(pk__in=notification_ids).select_related(
        'recipient'
    )
    for notification in rows:
        try:
            push.send_to_user(notification.recipient, notification)
        except Exception:  # noqa: BLE001 - one bad row must not stop the batch
            logger.exception('Push failed for notification %s', notification.pk)


@shared_task
def promote_scheduled_articles():
    return promote_due_articles()


@shared_task
def purge_notifications():
    """Drop read notifications past the retention window."""
    cutoff = timezone.now() - timedelta(days=READ_RETENTION_DAYS)
    deleted, _ = Notification.objects.filter(read_at__lt=cutoff).delete()
    return deleted
