from enum import Enum

from django.contrib.auth.models import User
from django.db import models


class SourceChoices(models.TextChoices):
    GOOGLE = 'from_oauth_google', 'Google'
    EMAIL = 'email_code', 'Email'


class EventTypeEnum(Enum):
    USER_CREATED = 'user.created'


class ClerkUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    source = models.CharField(
        choices=SourceChoices, default=SourceChoices.GOOGLE.value, max_length=50
    )
    clerk_id = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username
