from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class ReportReason(models.TextChoices):
    SPAM = 'spam', 'Spam'
    ABUSE_HATE = 'abuse_hate', 'Abuse or hate'
    MISINFORMATION = 'misinformation', 'Misinformation'
    COPYRIGHT = 'copyright', 'Copyright'
    OTHER = 'other', 'Other'


class Report(models.Model):
    reporter = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_reports',
    )
    content_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')
    reason = models.CharField(
        max_length=20, choices=ReportReason.choices, blank=True, default=''
    )
    # The reader's optional free-text detail (was `reason` before reasons were fixed).
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='third_side_reviewed_reports',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['reporter', 'content_type', 'object_id'],
                name='uniq_report_per_reporter_target',
            )
        ]

    def __str__(self):
        return f'Report #{self.id} on {self.content_type}:{self.object_id}'
