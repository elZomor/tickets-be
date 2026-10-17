from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True)
    order = models.PositiveIntegerField(default=0)
    group = models.ForeignKey(
        'third_side.NavGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categories',
    )
    # Position inside its group's menu (the group dictates its own order).
    group_order = models.PositiveIntegerField(default=0)
    show_in_nav = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    # Localized maps: {"ar": ..., "en": ..., "ro": ...}. `name` is the fallback.
    url_slug = models.JSONField(default=dict, blank=True)
    name_i18n = models.JSONField(default=dict, blank=True)
    tagline = models.JSONField(default=dict, blank=True)
    description = models.JSONField(default=dict, blank=True)
    image = models.ImageField(upload_to='third_side/categories', null=True, blank=True)
    image_url = models.CharField(max_length=300, blank=True, default='')
    hero_image_url = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name
