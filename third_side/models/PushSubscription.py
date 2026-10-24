from django.db import models


class PushSubscription(models.Model):
    """A browser's Web Push endpoint. One row per device; re-subscribing from
    another account moves the row to that account."""

    user = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_push_subscriptions',
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f'Push device of {self.user_id}'
