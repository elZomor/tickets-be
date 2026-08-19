from django.db import models

from utils.code_utils import upload_to_alt_spaces_festival_publication


class Publication(models.Model):
    file = models.FileField(upload_to=upload_to_alt_spaces_festival_publication)
    publication_number = models.CharField(max_length=20, null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    festival = models.ForeignKey(
        to='alt_spaces_festival.AltSpacesFestival',
        on_delete=models.DO_NOTHING,
        related_name='publications',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        festival_name = self.festival.name if self.festival_id else ''
        number = self.publication_number or ''
        if festival_name and number:
            return f'{festival_name} - {number}'
        return festival_name or number or str(self.pk)
