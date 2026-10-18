from django.db import models


class AboutPage(models.Model):
    """Singleton: the About page copy.

    `content` keeps the shape the page renders, with every text as a
    {"ar": ..., "en": ..., "ro": ...} map (resolved per ?lang= on read):
      {hero: {eyebrow, title, lead, body: [text], image, alt},
       topics: {title, body: [text], gallery: [{image, alt}]},
       journey: {title, items: [{year, title, text}]},
       principles: {title, items: [{title, text}]},
       why: {title: {before, highlight, after}, text,
             items: [{title, text}]},
       team: {title, members: [{name, role, image, alt}]}}
    """

    content = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = 'About page'

    def __str__(self):
        return 'About page'

    @classmethod
    def load(cls):
        return cls.objects.first() or cls()
