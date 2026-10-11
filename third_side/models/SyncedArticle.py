from django.db import models


class SyncedArticle(models.Model):
    payload_id = models.CharField(max_length=64, unique=True)
    data = models.JSONField()
    # One-to-one with the native Article this mirrors. Null until the
    # article has actually been pushed to Payload (see services.payload_sync).
    article = models.OneToOneField(
        'third_side.Article',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='synced_article',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.payload_id
