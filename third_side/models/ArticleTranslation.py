from django.db import models

from third_side.i18n import LOCALE_CHOICES


class ArticleTranslation(models.Model):
    """One language's version of an Article.

    title/slug/content (and the SEO title / meta description) are written from the
    admin editor (one row per language); excerpt is maintained Django-side.
    """

    article = models.ForeignKey(
        'third_side.Article', on_delete=models.CASCADE, related_name='translations'
    )
    locale = models.CharField(max_length=2, choices=LOCALE_CHOICES)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, allow_unicode=True)
    excerpt = models.TextField(blank=True, default='')
    # <title> for search engines; the article title is used when blank.
    seo_title = models.CharField(max_length=255, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')
    # Lexical JSON ({"root": {...}}) as produced by the admin editor.
    content = models.JSONField(null=True, blank=True)
    is_ai_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ['article_id', 'locale']
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'locale'], name='uniq_translation_per_locale'
            ),
            models.UniqueConstraint(
                fields=['locale', 'slug'], name='uniq_translation_slug_per_locale'
            ),
        ]

    def __str__(self):
        return f'{self.article_id}:{self.locale}'
