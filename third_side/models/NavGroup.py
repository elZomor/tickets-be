from django.db import models


class NavGroup(models.Model):
    """A header group of categories, e.g. Visual Arts / Written Arts.

    Localized fields are {"ar": ..., "en": ..., "ro": ...} maps.
    """

    slug = models.SlugField(max_length=60, unique=True)
    order = models.PositiveIntegerField(default=0)
    url_slug = models.JSONField(default=dict, blank=True)
    label = models.JSONField(default=dict, blank=True)
    tagline = models.JSONField(default=dict, blank=True)
    description = models.JSONField(default=dict, blank=True)
    image = models.ImageField(upload_to='third_side/groups', null=True, blank=True)
    image_url = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.slug
