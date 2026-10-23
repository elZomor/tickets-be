from django.db import models


class EmailAudience(models.TextChoices):
    DIRECT = 'direct', 'Direct'
    # Everyone who opted in; not available yet (needs consent + unsubscribe).
    SUBSCRIBERS = 'subscribers', 'Subscribers'


class EmailStatus(models.TextChoices):
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'


class OutgoingEmail(models.Model):
    """An email an editor composed in the admin and sent from their own address."""

    sender = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='third_side_sent_emails',
    )
    from_email = models.EmailField()
    to = models.JSONField(default=list)
    cc = models.JSONField(default=list, blank=True)
    subject = models.CharField(max_length=255)
    direction = models.CharField(max_length=3, default='rtl')
    doc = models.JSONField(null=True, blank=True)
    html = models.TextField()
    audience = models.CharField(
        max_length=12, choices=EmailAudience.choices, default=EmailAudience.DIRECT
    )
    status = models.CharField(max_length=6, choices=EmailStatus.choices)
    provider_message_id = models.CharField(max_length=255, blank=True, default='')
    error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.subject} ({self.status})'
