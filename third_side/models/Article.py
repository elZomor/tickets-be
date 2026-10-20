from django.db import models

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
    PUBLISHED = 'PUBLISHED', 'Published'
    ARCHIVED = 'ARCHIVED', 'Archived'
    REJECTED = 'REJECTED', 'Rejected'
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
        to='third_side.ThirdSideUser',
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
    # A reader submission: the author lets us machine-translate it.
    allow_translation = models.BooleanField(default=True)
    # Highlighted on its category page.
    is_featured = models.BooleanField(default=False)
    # True when a reader submitted it on the website; False when it was created
    # by an editor in the admin.
    via_website = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.title
