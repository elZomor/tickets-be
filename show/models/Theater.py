from django.db import models

from utils.json_utils import default_localized_model


class Theater(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=0)
    location = models.URLField(null=True)

    def __str__(self):
        return self.name
