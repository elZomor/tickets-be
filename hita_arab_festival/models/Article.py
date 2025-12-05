from django.db import models

from hita_arab_festival.models import Show, ArabFestival


class Tags(models.TextChoices):
    SHOW = 'SHOW', 'Show'
    FEST = 'FESTIVAL', 'Festival'


class ArticleType(models.TextChoices):
    ARTICLE = 'ARTICLE', 'Article'
    SYMPOSIA = 'SYMPOSIA', 'Symposia'
    CREATIVITY = 'CREATIVITY', 'Creativity'


class Article(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    show = models.ForeignKey(
        Show,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='show_articles',
    )
    festival = models.ForeignKey(
        ArabFestival,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='festival_articles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.CharField(max_length=50)
    tag = models.CharField(max_length=50, choices=Tags.choices, default=Tags.FEST)
    article_type = models.CharField(
        max_length=50, choices=ArticleType.choices, default=ArticleType.ARTICLE
    )

    @property
    def article_attachments_list(self):
        return (
            self.article_attachments.all()
            .order_by('position')
            .values_list('file', flat=True)
        )
