from django.db import models

from hita.models.Lookups import PublicChannelTypes


class PublicChannel(models.Model):
    performer = models.ForeignKey(
        'hita.Performer', on_delete=models.CASCADE, related_name='public_channel_list'
    )
    channel_type = models.CharField(
        max_length=20,
        choices=PublicChannelTypes.choices,
        default=PublicChannelTypes.YOUTUBE.value,
    )
    channel_info = models.CharField(max_length=100)

    class Meta:
        ordering = ('channel_type',)
