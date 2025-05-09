from django.db import models

from utils.code_utils import upload_to_publication


class Publication(models.Model):
    file = models.FileField(upload_to=upload_to_publication)
    publication_number = models.CharField(max_length=20, null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    festival = models.ForeignKey(to='show.Festival', on_delete=models.DO_NOTHING, related_name='publications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.publication_number + ' - ' + self.festival.name