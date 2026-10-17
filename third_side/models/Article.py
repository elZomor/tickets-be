import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from third_side.i18n import DEFAULT_LOCALE, LOCALE_CHOICES
from third_side.models.Category import Category
from third_side.models.Critic import Critic
from third_side.models.Tag import Tag

logger = logging.getLogger(__name__)


class ArticleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
    READY_FOR_EDITING = 'READY_FOR_EDITING', 'Ready for Editing'
    READY_FOR_PUBLISHING = 'READY_FOR_PUBLISHING', 'Ready for Publishing'
    PUBLISHED = 'PUBLISHED', 'Published'
    ARCHIVED = 'ARCHIVED', 'Archived'
    REPORTED = 'REPORTED', 'Reported'


class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, allow_unicode=True)
    category = models.ForeignKey(
        to=Category, on_delete=models.PROTECT, related_name='articles'
    )
    critic = models.ForeignKey(
        to=Critic, on_delete=models.PROTECT, related_name='articles'
    )
    content = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=24, choices=ArticleStatus.choices, default=ArticleStatus.DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='third_side_articles',
    )
    is_hidden = models.BooleanField(default=False)
    share_count = models.PositiveIntegerField(default=0)
    read_count = models.PositiveIntegerField(default=0)
    # The language the article was written in; the others are translations.
    original_language = models.CharField(
        max_length=2, choices=LOCALE_CHOICES, default=DEFAULT_LOCALE
    )
    cover = models.ImageField(upload_to='third_side/covers', null=True, blank=True)
    cover_url = models.CharField(max_length=300, blank=True, default='')
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles')
    # Highlighted on its category page.
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.title


@receiver(pre_save, sender=Article)
def _cache_old_status(sender, instance, **kwargs):
    instance._old_status = (
        sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=Article)
def _push_to_payload_on_ready_for_editing(sender, instance, **kwargs):
    # Editors approve the article internally up to READY_FOR_EDITING, then it
    # moves into Payload for the writer-facing editing/review loop. Only the
    # transition into that state (not every save while already in it) should
    # create the Payload-side article.
    if instance.status != ArticleStatus.READY_FOR_EDITING:
        return
    if getattr(instance, '_old_status', None) == ArticleStatus.READY_FOR_EDITING:
        return

    from third_side.services.payload_sync import ensure_synced_article

    try:
        ensure_synced_article(instance)
    except Exception:
        logger.exception('Failed to push article %s to Payload', instance.pk)
