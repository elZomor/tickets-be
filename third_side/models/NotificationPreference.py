from django.db import models


class NotificationPreference(models.Model):
    """What a reader wants pushed. The inbox always records everything; these
    switches only gate the push."""

    user = models.OneToOneField(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_notification_preference',
    )
    push_enabled = models.BooleanField(default=True)
    status = models.BooleanField(default=True)
    profile = models.BooleanField(default=True)
    reports = models.BooleanField(default=True)
    activity = models.BooleanField(default=True)
    follows = models.BooleanField(default=True)

    def __str__(self):
        return f'Notification preferences of {self.user_id}'
