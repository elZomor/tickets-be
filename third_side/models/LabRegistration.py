from django.db import models


class RegistrationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending review'
    ACCEPTED = 'accepted', 'Accepted'
    WAITLISTED = 'waitlisted', 'Waitlisted'
    REJECTED = 'rejected', 'Rejected'
    CANCELLED = 'cancelled', 'Cancelled'


class LabRegistration(models.Model):
    """A reader's seat (or application) in a Lab program."""

    program = models.ForeignKey(
        to='third_side.LabProgram',
        on_delete=models.CASCADE,
        related_name='registrations',
    )
    user = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='lab_registrations',
    )
    status = models.CharField(
        max_length=10,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING,
    )
    # {motivation, phone}
    answers = models.JSONField(default=dict, blank=True)
    attended = models.BooleanField(default=False)
    note = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['program', 'user'], name='uniq_lab_registration'
            )
        ]

    def __str__(self):
        return f'{self.user_id} in {self.program_id} ({self.status})'
