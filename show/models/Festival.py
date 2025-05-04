from django.db import models
from django.utils import timezone

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
    organizing_team = models.JSONField(null=True, blank=True)

    @property
    def festival_status(self):
        if timezone.now().date() < self.start_date:
            return 'Soon'
        if timezone.now().date() <= self.end_date:
            return 'Running'
        return 'Finished'

    def __str__(self):
        return self.name