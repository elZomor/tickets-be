from django.db import models

from utils.code_utils import upload_to_festival


class Festival(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    organizer = models.CharField(max_length=100, null=True, blank=True)
    jury_list = models.JSONField(null=True, blank=True)
    awards = models.JSONField(null=True, blank=True)
    extra_details = models.JSONField(null=True, blank=True)
    logo = models.FileField(upload_to=upload_to_festival, null=True, blank=True)

    @property
    def festival_status(self):
        return None