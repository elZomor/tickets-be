from django.db import models

from utils.json_utils import default_localized_model


class ShowTag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
