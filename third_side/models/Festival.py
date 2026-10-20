from django.db import models


class Festival(models.Model):
    """A festival shown as a card on the Festivals page; its posts form the feed.

    Localized fields are {"ar": ..., "en": ..., "ro": ...} maps; `slug` is the
    canonical (fallback) URL segment, `slug_i18n` the one per locale.
    """

    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True)
    slug_i18n = models.JSONField(default=dict, blank=True)
    name_i18n = models.JSONField(default=dict, blank=True)
    description_i18n = models.JSONField(default=dict, blank=True)
    location_i18n = models.JSONField(default=dict, blank=True)
    cover = models.ImageField(upload_to='third_side/festivals', null=True, blank=True)
    cover_url = models.CharField(max_length=300, blank=True, default='')
    starts_on = models.DateField()
    ends_on = models.DateField()
    # Key of the frontend mock record this row was seeded from.
    mock_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-starts_on', '-id']

    def __str__(self):
        return self.slug
