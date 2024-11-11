from django.db import models

from hita.models import HITAMember


class RequestTypeChoices(models.Choices):
    VIEW_CONTACT_DETAILS = 'CONTACT_DETAILS', 'View Contact Details'
    VIEW_GALLERY = 'GALLERY', 'View Gallery'


class RequestStatus(models.Choices):
    APPROVED = 'APPROVED', 'Approved'
    PENDING = 'PENDING', 'Pending'
    REJECTED = 'REJECTED', 'Rejected'


class NotificationCenter(models.Model):
    performer = models.ForeignKey(
        HITAMember, on_delete=models.CASCADE, related_name='notifications'
    )
    request_from = models.ForeignKey(
        HITAMember, on_delete=models.DO_NOTHING, related_name='requests'
    )
    request_type = models.CharField(
        max_length=20,
        choices=RequestTypeChoices.choices,
        default=RequestTypeChoices.VIEW_CONTACT_DETAILS.value,
    )
    message = models.CharField(max_length=250, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=RequestStatus, default=RequestStatus.PENDING.value
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
