from django.db import models

from utils.json_utils import default_localized_model


class ShowTag(models.Model):
    name = models.JSONField(default=default_localized_model)

    def __str__(self):
        return self.name.get('ar')