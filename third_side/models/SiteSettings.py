from django.db import models


class SiteSettings(models.Model):
    """Singleton for site-wide copy: hero, contact, social links, sponsors.

    hero:     {image, title{loc}, subtitle{loc}, cta_url{loc}}
    contact:  {email, phone, address{loc}}
    social:   [{network, url}]
    sponsors: [{id, name{loc}, url, logo?}]
    """

    hero = models.JSONField(default=dict, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    social = models.JSONField(default=list, blank=True)
    sponsors = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name_plural = 'Site settings'

    def __str__(self):
        return 'Site settings'

    @classmethod
    def load(cls):
        return cls.objects.first() or cls()
