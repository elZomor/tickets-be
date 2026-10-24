from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class ModerationActionType(models.TextChoices):
    DISMISS = 'dismiss', 'Dismiss'
    HIDE = 'hide', 'Hide'
    WARN = 'warn', 'Warn'
    DELETE = 'delete', 'Delete'
    SUSPEND = 'suspend', 'Suspend'


# Actions that count against the author when judging a repeat offender.
STRIKE_ACTIONS = (
    ModerationActionType.WARN,
    ModerationActionType.DELETE,
    ModerationActionType.SUSPEND,
)


class ModerationAction(models.Model):
    """What a moderator decided about a reported target, kept as author history."""

    report = models.ForeignKey(
        to='third_side.Report',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions',
    )
    content_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')
    author = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderation_actions',
    )
    moderator = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='third_side_moderation_done',
    )
    action = models.CharField(max_length=10, choices=ModerationActionType.choices)
    note = models.TextField(blank=True, default='')
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        permissions = [('suspend_user', 'Can suspend users from moderation')]

    def __str__(self):
        return f'{self.action} on {self.content_type}:{self.object_id}'
