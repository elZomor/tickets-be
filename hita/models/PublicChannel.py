from django.db import models

from hita.models import ContactType


class PublicChannel(models.Model):
    performer = models.ForeignKey(
        'hita.Performer', on_delete=models.CASCADE, related_name='public_channel_list'
    )
    channel_type = models.CharField(
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.YOUTUBE.value,
    )
    channel_info = models.CharField(max_length=100)

    class Meta:
        ordering = ('channel_type',)
