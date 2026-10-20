from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from third_side.i18n import LOCALE_CHOICES


class FestivalPostType(models.TextChoices):
    TEXT = 'text'
    TITLED_TEXT = 'titled_text'
    IMAGE = 'image'
    IMAGE_CAPTION = 'image_caption'
    VIDEO = 'video'
    VIDEO_CAPTION = 'video_caption'
    ARTICLE = 'article'


class VideoKind(models.TextChoices):
    EMBED = 'embed'
    FILE = 'file'


IMAGE_TYPES = (FestivalPostType.IMAGE, FestivalPostType.IMAGE_CAPTION)
VIDEO_TYPES = (FestivalPostType.VIDEO, FestivalPostType.VIDEO_CAPTION)


class FestivalPost(models.Model):
    """One entry of the festivals feed. Which fields apply depends on `type`."""

    festival = models.ForeignKey(
        'third_side.Festival', on_delete=models.CASCADE, related_name='posts'
    )
    type = models.CharField(max_length=20, choices=FestivalPostType.choices)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_published = models.BooleanField(default=True)
    # Language the text was written in; shown as-is for the other locales.
    original_language = models.CharField(
        max_length=2, choices=LOCALE_CHOICES, default='ar'
    )
    title_i18n = models.JSONField(default=dict, blank=True)
    body_i18n = models.JSONField(default=dict, blank=True)
    caption_i18n = models.JSONField(default=dict, blank=True)
    article = models.ForeignKey(
        'third_side.Article',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='festival_posts',
    )
    video_kind = models.CharField(
        max_length=10, choices=VideoKind.choices, default=VideoKind.EMBED
    )
    # Watch URL (embed: YouTube/Vimeo) or, for `file`, used when no upload is set.
    video_url = models.CharField(max_length=1000, blank=True, default='')
    video_file = models.FileField(
        upload_to='third_side/festival-videos', null=True, blank=True
    )
    poster = models.ImageField(
        upload_to='third_side/festival-posters', null=True, blank=True
    )
    poster_url = models.CharField(max_length=1000, blank=True, default='')
    # Key of the frontend mock record this row was seeded from.
    mock_id = models.PositiveIntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ['-published_at', '-id']
        indexes = [models.Index(fields=['festival', '-published_at'])]

    def __str__(self):
        return f'{self.festival_id} {self.type} {self.published_at:%Y-%m-%d %H:%M}'

    def clean(self):
        errors = {}
        if self.type == FestivalPostType.TITLED_TEXT and not self.title_i18n:
            errors['title_i18n'] = 'A titled text post needs a title.'
        if self.type in (FestivalPostType.TEXT, FestivalPostType.TITLED_TEXT) and (
            not self.body_i18n
        ):
            errors['body_i18n'] = 'A text post needs a body.'
        if self.type in VIDEO_TYPES and not (self.video_url or self.video_file):
            errors['video_url'] = 'A video post needs a video URL or file.'
        if self.type == FestivalPostType.ARTICLE and not self.article_id:
            errors['article'] = 'An article post needs an article.'
        if errors:
            raise ValidationError(errors)


class FestivalPostMedia(models.Model):
    """An image of an `image` / `image_caption` post (shown in `order`)."""

    post = models.ForeignKey(
        'third_side.FestivalPost', on_delete=models.CASCADE, related_name='media'
    )
    image = models.ImageField(
        upload_to='third_side/festival-posts', null=True, blank=True
    )
    image_url = models.CharField(max_length=1000, blank=True, default='')
    alt_i18n = models.JSONField(default=dict, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = 'Festival post media'
