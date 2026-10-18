from django.db import models


class PayloadSyncStatus(models.TextChoices):
    # Row exists but the article is not in Payload yet (queued or retrying).
    PENDING = 'pending', 'Pending'
    SYNCED = 'synced', 'Synced'
    # Retries exhausted; the sweeper and the admin action can still retry.
    FAILED = 'failed', 'Failed'


class SyncedArticle(models.Model):
    # Null until Payload has created the doc (see services.payload_sync).
    payload_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    # One-to-one with the native Article this mirrors. Null for docs that
    # were created in Payload directly and never linked to an Article.
    article = models.OneToOneField(
        'third_side.Article',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='synced_article',
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Push to Payload bookkeeping. Rows that came from Payload's webhook are
    # already synced, hence the default.
    sync_status = models.CharField(
        max_length=10,
        choices=PayloadSyncStatus.choices,
        default=PayloadSyncStatus.SYNCED,
        db_index=True,
    )
    sync_attempts = models.PositiveIntegerField(default=0)
    sync_error = models.TextField(blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.payload_id or f'pending:{self.article_id}'
