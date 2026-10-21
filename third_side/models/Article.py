from django.db import models

from third_side.utils import AsciiUploadTo
from django.db.models import Q
from django.utils import timezone

from third_side.i18n import DEFAULT_LOCALE, LOCALE_CHOICES
from third_side.models.Category import Category
from third_side.models.Critic import Critic
from third_side.models.Tag import Tag


class ArticleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
    READY_FOR_EDITING = 'READY_FOR_EDITING', 'Ready for Editing'
    READY_FOR_PUBLISHING = 'READY_FOR_PUBLISHING', 'Ready for Publishing'
    SCHEDULED = 'SCHEDULED', 'Scheduled'
    PUBLISHED = 'PUBLISHED', 'Published'
    ARCHIVED = 'ARCHIVED', 'Archived'
    REJECTED = 'REJECTED', 'Rejected'
    REPORTED = 'REPORTED', 'Reported'


def live_q(prefix=''):
    """Articles readers can see: published, or scheduled and now due.

    `prefix` reaches the article through a relation (e.g. 'article__').
    """
    return Q(**{f'{prefix}status': ArticleStatus.PUBLISHED}) | Q(
        **{
            f'{prefix}status': ArticleStatus.SCHEDULED,
            f'{prefix}published_at__lte': timezone.now(),
        }
    )


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
    # When it went (or goes, for SCHEDULED) live.
    published_at = models.DateTimeField(null=True, blank=True)
    # The editor in charge of the article, if one is assigned.
    editor = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'EDITOR'},
        related_name='third_side_edited_articles',
    )
    created_by = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='third_side_articles',
    )
    is_hidden = models.BooleanField(default=False)
    # SEO: keep out of search engines / point search engines at another URL.
    noindex = models.BooleanField(default=False)
    canonical_url = models.URLField(max_length=1000, blank=True, default='')
    share_count = models.PositiveIntegerField(default=0)
    read_count = models.PositiveIntegerField(default=0)
    # The language the article was written in; the others are translations.
    original_language = models.CharField(
        max_length=2, choices=LOCALE_CHOICES, default=DEFAULT_LOCALE
    )
    cover = models.ImageField(
        upload_to=AsciiUploadTo('third_side/covers'), null=True, blank=True
    )
    cover_url = models.CharField(max_length=1000, blank=True, default='')
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles')
    # A reader submission: the author lets us machine-translate it.
    allow_translation = models.BooleanField(default=True)
    # Highlighted on its category page.
    is_featured = models.BooleanField(default=False)
    # True when a reader submitted it on the website; False when it was created
    # by an editor in the admin.
    via_website = models.BooleanField(default=False)
    # Images a reader attached to a website submission; the editor finds them
    # appended to the body when the article is first opened in the admin.
    submitted_media = models.ManyToManyField(
        'third_side.Media', blank=True, related_name='submissions'
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.title
