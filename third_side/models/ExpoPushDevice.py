from django.db import models


class ExpoPushDevice(models.Model):
    """A phone's Expo push token (the mobile app). One row per device;
    registering from another account moves the row to that account."""

    user = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_expo_devices',
    )
    token = models.CharField(max_length=200, unique=True)
    platform = models.CharField(max_length=10, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f'Expo device of {self.user_id}'
