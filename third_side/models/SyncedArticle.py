from django.db import models


class SyncedArticle(models.Model):
    payload_id = models.CharField(max_length=64, unique=True)
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.payload_id
