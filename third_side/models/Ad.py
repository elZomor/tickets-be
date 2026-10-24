from django.db import models

from third_side.i18n import default_locales


# Creative sizes (the site's ad slots; upload at 2x). The first four are the
# design's placements: slim 1420x120 and banner 1420x240 run across the content
# column, box 380x395 sits beside a category's main article, column 307x454
# beside an article's title. rect 300x250 is the phone version of slim/banner.
AD_SIZES = ('slim', 'banner', 'box', 'column', 'rect')
# Sizes older clients still request, and what they now get.
LEGACY_AD_SIZES = {'tall': 'rect', 'wide': 'rect'}


class AdType(models.TextChoices):
    EVENT = 'event', 'Event'
    SPONSOR = 'sponsor', 'Sponsor'


class Ad(models.Model):
    """Our own ad (sponsor or event), not an ad network. Counters are first-party.

    images: {"ar": {"slim": url, "banner": url, "box": url, ...}, "en": {...}, "ro": {...}}
    alt:    {"ar": text, ...}
    Sizes: see AD_SIZES. Keys saved before the redesign (tall, wide) are ignored.
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
