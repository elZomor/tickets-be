from django.db import models


class NotificationType(models.TextChoices):
    ARTICLE_STATUS = 'article_status', 'Article status'
    PROFILE_UPDATED = 'profile_updated', 'Profile updated'
    REPORT_REVIEWED = 'report_reviewed', 'Report reviewed'
    CONTENT_REPORTED = 'content_reported', 'Content reported'
    ARTICLE_COMMENT = 'article_comment', 'New comment'
    ARTICLE_RATING = 'article_rating', 'New rating'
    NEW_ARTICLE = 'new_article', 'New article'
    NEW_FESTIVAL_POST = 'new_festival_post', 'New festival post'


class Notification(models.Model):
    """One inbox entry. Holds the type and its params, never display text: the
    frontend renders the copy from its dictionaries, the push sender from
    services/push.py."""

    recipient = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_notifications',
    )
    type = models.CharField(max_length=24, choices=NotificationType.choices)
    params = models.JSONField(default=dict, blank=True)
    # Events folded into this row (comments / ratings on one article).
    count = models.PositiveIntegerField(default=1)
    dedupe_key = models.CharField(max_length=120)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['recipient', 'dedupe_key'], name='uniq_notification_dedupe'
            )
        ]
        indexes = [
            models.Index(fields=['recipient', '-updated_at']),
            models.Index(fields=['recipient', 'read_at']),
        ]

    def __str__(self):
        return f'{self.type} for {self.recipient_id}'
