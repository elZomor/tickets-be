from django.utils import timezone

from django.contrib.auth.models import User
from django.db import models

from show.models import Theater
from show.models.ShowTag import ShowTag
from utils.code_utils import upload_to
from utils.json_utils import default_localized_model


class ShowStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    SPAM = 'SPAM', 'Spam'
    INAPPROPRIATE = 'INAPPROPRIATE', 'Inappropriate'


class Show(models.Model):
    name = models.JSONField(default=default_localized_model)
    link = models.URLField()
    time = models.DateTimeField()
    cast_name = models.CharField(max_length=100, null=True, blank=True)
    poster = models.FileField(upload_to=upload_to, null=True, blank=True)
    author = models.CharField(max_length=50)
    director = models.CharField(max_length=50)
    description = models.TextField(max_length=250, null=True, blank=True)
    theater = models.ForeignKey(to=Theater, on_delete=models.DO_NOTHING)
    initial_reserved_seats = models.IntegerField(default=0)
    reserved_seats = models.IntegerField(default=0)
    status = models.CharField(
        choices=ShowStatus.choices, default=ShowStatus.PENDING.value, max_length=50
    )
    created_by = models.ForeignKey(
        to=User, on_delete=models.DO_NOTHING, related_name='created_by'
    )
    reviewed_by = models.ForeignKey(
        to=User, on_delete=models.DO_NOTHING, related_name='reviewed_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(to=ShowTag, blank=True)

    @property
    def remaining_seats(self):
        return (
            self.theater.capacity - self.initial_reserved_seats - self.reserved_seats
            or 0
        )

    @property
    def is_open(self):
        return timezone.now() < self.time

    def __str__(self):
        return f'{self.name.get('ar')} - {self.cast_name}'
