from django.conf import settings
from django.db import models

from third_side.models.Category import Category
from third_side.models.Critic import Critic


class ArticleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'


class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    category = models.ForeignKey(to=Category, on_delete=models.PROTECT, related_name='articles')
    critic = models.ForeignKey(to=Critic, on_delete=models.PROTECT, related_name='articles')
    content = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=ArticleStatus.choices, default=ArticleStatus.DRAFT
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

    def __str__(self):
        return self.title
