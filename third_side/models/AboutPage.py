from django.db import models


class AboutPage(models.Model):
    """Singleton: the About page copy.

    `content` keeps the shape the page renders, with every text as a
    {"ar": ..., "en": ..., "ro": ...} map:
      {eyebrow, title, hero_image, hero_alt,
       sections: [{lead, body: [text]}],
       gallery: [{image, alt}], values: [{id, title, text}]}
    """

    content = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = 'About page'

    def __str__(self):
        return 'About page'

    @classmethod
    def load(cls):
        return cls.objects.first() or cls()
