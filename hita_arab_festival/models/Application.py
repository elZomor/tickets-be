from django.contrib.auth.models import User
from django.db import models

from hita_arab_festival.models.Festival import ArabFestival
from utils.code_utils import (
    upload_to_arab_festival_application_national_id,
    upload_to_arab_festival_application_script,
)

SCRIPT_EXTENSIONS = ['.pdf', '.doc', '.docx']
SCRIPT_MAX_MB = 20
NATIONAL_ID_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.webp']
NATIONAL_ID_MAX_MB = 10


class Department(models.TextChoices):
    ACTING_DIRECTING = 'ACTING_DIRECTING', 'تمثيل وإخراج'
    DRAMA_CRITICISM = 'DRAMA_CRITICISM', 'دراما ونقد'
    DECOR = 'DECOR', 'ديكور'


class StudyType(models.TextChoices):
    CREDIT_HOURS = 'CREDIT_HOURS', 'ساعات معتمدة'
    PARALLEL = 'PARALLEL', 'موازي'


class ApplicationStatus(models.TextChoices):
    PENDING = 'PENDING', 'قيد المراجعة'
    ACCEPTED = 'ACCEPTED', 'مقبول'
    REJECTED = 'REJECTED', 'مرفوض'


class Application(models.Model):
    festival = models.ForeignKey(
        ArabFestival, on_delete=models.CASCADE, related_name='applications'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='arab_festival_applications',
    )
    email = models.EmailField()
    show_name = models.CharField(max_length=200)
    director_name = models.CharField(max_length=200)
    department = models.CharField(max_length=32, choices=Department.choices)
    study_type = models.CharField(max_length=32, choices=StudyType.choices)
    author = models.CharField(max_length=200)
    dramaturgy = models.CharField(max_length=200, blank=True, default='')
    mobile = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20)
    actors = models.JSONField(default=list)
    script = models.FileField(upload_to=upload_to_arab_festival_application_script)
    directorial_vision = models.TextField()
    show_summary = models.TextField()
    national_id = models.FileField(
        upload_to=upload_to_arab_festival_application_national_id
    )
    status = models.CharField(
        max_length=16,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['festival', 'email'],
                name='unique_application_per_festival_email',
            )
        ]

    def __str__(self):
        return f'{self.show_name} - {self.director_name}'
