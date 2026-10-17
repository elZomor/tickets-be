from django.db import models

from third_side.utils import upload_to_critic_photo


class Critic(models.Model):
    name = models.CharField(max_length=150)
    bio = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to=upload_to_critic_photo, null=True, blank=True)
    photo_url = models.CharField(max_length=300, blank=True, default='')
    # Localized maps {"ar": ..., "en": ..., "ro": ...}; `name`/`bio` are the fallback.
    name_i18n = models.JSONField(default=dict, blank=True)
    bio_i18n = models.JSONField(default=dict, blank=True)
    # URL segment per locale (the writer's page lives at /<locale>/writers/<slug>).
    slug_i18n = models.JSONField(default=dict, blank=True)
    main_category = models.ForeignKey(
        'third_side.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='main_critics',
    )

    def __str__(self):
        return self.name
