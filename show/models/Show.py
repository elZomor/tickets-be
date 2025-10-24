from datetime import datetime

from django.utils import timezone

from django.contrib.auth.models import User
from django.db import models

from show.models.ShowTag import ShowTag
from utils.code_utils import upload_to_show


class ShowStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    SPAM = 'SPAM', 'Spam'
    INAPPROPRIATE = 'INAPPROPRIATE', 'Inappropriate'


class Show(models.Model):
    name = models.CharField(max_length=100)
    link = models.URLField(null=True, blank=True)
    cast_name = models.CharField(max_length=100, null=True, blank=True)
    poster = models.FileField(upload_to=upload_to_show, null=True, blank=True)
    author = models.CharField(max_length=50)
    director = models.CharField(max_length=50)
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
    notes = models.JSONField(null=True, blank=True)
    cast = models.JSONField(null=True, blank=True)
    crew = models.JSONField(null=True, blank=True)
    festival = models.ForeignKey(
        to='show.Festival',
        on_delete=models.DO_NOTHING,
        related_name='shows',
        null=True,
        blank=True,
    )
    cast_note = models.TextField(null=True, blank=True)
    show_description = models.TextField(null=True, blank=True)

    def _get_cached_dates(self):
        if hasattr(self, '_cached_dates'):
            return self._cached_dates
        dates = list(self.dates.all())
        self._cached_dates = dates
        return dates

    @property
    def has_multiple_nights(self):
        return len(self._get_cached_dates()) > 1

    @property
    def nearest_night(self):
        now = timezone.now()
        tz = timezone.get_current_timezone()

        dates = self._get_cached_dates()

        valid_dates = [
            (d, datetime.combine(d.date, d.time).replace(tzinfo=tz))
            for d in dates
            if datetime.combine(d.date, d.time).replace(tzinfo=tz) >= now
        ]

        nearest = min(valid_dates, key=lambda x: x[1], default=None)
        if nearest:
            return nearest[0]

        past_dates = [
            (d, datetime.combine(d.date, d.time).replace(tzinfo=tz))
            for d in dates
            if datetime.combine(d.date, d.time).replace(tzinfo=tz) <= now
        ]

        nearest = max(past_dates, key=lambda x: x[1], default=None)
        return nearest[0]

    @property
    def is_open(self):
        current_datetime = timezone.now()
        return any(
            date_obj.date == current_datetime.date()
            and date_obj.time >= current_datetime.time()
            for date_obj in self._get_cached_dates()
        )

    def __str__(self):
        return f'{self.name} - {self.cast_name}'
