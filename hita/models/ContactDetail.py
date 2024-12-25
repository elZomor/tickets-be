from django.db import models

from hita.models.Lookups import ContactTypes, ContactSpecificType


class ContactDetail(models.Model):
    performer = models.ForeignKey(
        'hita.Performer', on_delete=models.CASCADE, related_name='contact_detail_list'
    )
    contact_type = models.CharField(
        max_length=20,
        choices=ContactTypes,
        default=ContactSpecificType.MOBILE.value,
    )
    contact_info = models.CharField(max_length=100)

    class Meta:
        ordering = ('contact_type',)
