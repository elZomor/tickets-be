from django.db import models

from hita.models import Performer


class Achievement(models.Model):
    performer = models.ForeignKey(
        Performer, on_delete=models.CASCADE, related_name='achievements'
    )
    position = models.CharField(max_length=100)
    field = models.CharField(max_length=100)
    show_name = models.CharField(max_length=100)
    festival_name = models.CharField(max_length=100)
    year = models.IntegerField()
