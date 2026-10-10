from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    EDITOR = 'EDITOR', 'Editor'
    READER = 'READER', 'Reader'


class Profile(models.Model):
    user = models.OneToOneField(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='third_side_profile',
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.READER)

    def __str__(self):
        return f'{self.user} ({self.role})'
