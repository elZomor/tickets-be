from django.db import models
from django.utils import timezone

from utils.code_utils import upload_to_global_festival_show


class ShowStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    SPAM = 'SPAM', 'Spam'
    INAPPROPRIATE = 'INAPPROPRIATE', 'Inappropriate'


class Show(models.Model):
    name = models.CharField(max_length=100)
    link = models.URLField(null=True, blank=True)
    poster = models.FileField(
        upload_to=upload_to_global_festival_show, null=True, blank=True
    )
    author = models.CharField(max_length=50)
    director = models.CharField(max_length=50)
    reserved_seats = models.IntegerField(default=0)
    status = models.CharField(
        choices=ShowStatus.choices, default=ShowStatus.PENDING.value, max_length=50
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.JSONField(null=True, blank=True)
    cast = models.JSONField(null=True, blank=True)
    crew = models.JSONField(null=True, blank=True)
    festival = models.ForeignKey(
        to='global_festival.GlobalFestival',
        on_delete=models.DO_NOTHING,
        related_name='shows',
        null=True,
        blank=True,
    )
    cast_word = models.TextField(null=True, blank=True)
    show_description = models.TextField(null=True, blank=True)
    date = models.DateField()
    time = models.TimeField()
    venue_name = models.CharField(max_length=50)
    venue_location = models.URLField()
    allowed_seats = models.IntegerField()
    allowed_waiting = models.IntegerField()
    reservation_status_open = models.BooleanField(default=False)
    open_for_comments = models.BooleanField(default=False)
    reservation_hash = models.CharField(max_length=64, null=True, blank=True, unique=True, default=None)

    @property
    def is_open(self):
        current_datetime = timezone.now()
        return (
            self.date == current_datetime.date()
            and self.time >= current_datetime.time()
        )

    @property
    def reservation_status(self):
        from global_festival.models.Reservation import ReservationStatus

        if self.reserved_seats >= self.allowed_seats + self.allowed_waiting:
            return None
        elif self.reserved_seats >= self.allowed_seats:
            return ReservationStatus.WAITING_LIST
        else:
            return ReservationStatus.CONFIRMED

    @property
    def is_open_for_reservation(self):
        from global_festival.models.Reservation import ReservationStatus

        if not self.reservation_status_open:
            return ReservationStatus.CLOSED
        reservation_status = self.reservation_status
        if not reservation_status:
            return ReservationStatus.COMPLETE
        if reservation_status == ReservationStatus.WAITING_LIST:
            return ReservationStatus.OPEN_FOR_WAITING_LIST
        return ReservationStatus.OPEN_FOR_RESERVATION

    @property
    def articles(self):
        return self.show_articles.all()

    @property
    def is_comment_allowed(self):
        return self.open_for_comments

    def __str__(self):
        return f'{self.name}'
