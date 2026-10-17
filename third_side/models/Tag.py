from django.db import models


class Tag(models.Model):
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True)
    url_slug = models.JSONField(default=dict, blank=True)
    name = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        return self.slug
