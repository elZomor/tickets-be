from django.db import models

from third_side.i18n import default_locales


class AdType(models.TextChoices):
    EVENT = 'event', 'Event'
    SPONSOR = 'sponsor', 'Sponsor'


class Ad(models.Model):
    """Our own ad (sponsor or event), not an ad network. Counters are first-party.

    images: {"ar": {"tall": url, "rect": url, "wide": url}, "en": {...}, "ro": {...}}
    alt:    {"ar": text, ...}
    Creative sizes: tall 300x600, rect 300x250, wide 970x250 (home banner).
    An ad is only picked for sizes it has an image for.
    """

    type = models.CharField(max_length=10, choices=AdType.choices)
    name = models.CharField(max_length=150)
    url = models.CharField(max_length=500)
    # Internal urls are site paths (e.g. /about) and get the locale prefix.
    internal = models.BooleanField(default=False)
    locales = models.JSONField(default=default_locales)
    starts_at = models.DateField()
    ends_at = models.DateField()
    weight = models.PositiveIntegerField(default=1)
    alt = models.JSONField(default=dict, blank=True)
    images = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    impressions = models.PositiveBigIntegerField(default=0)
    clicks = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ['-starts_at', 'id']

    def __str__(self):
        return self.name
