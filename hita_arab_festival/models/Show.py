from django.db import models
from django.utils import timezone

from utils.code_utils import upload_to_arabic_festival_show


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
        upload_to=upload_to_arabic_festival_show, null=True, blank=True
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
        to='hita_arab_festival.ArabFestival',
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

    @property
    def is_open(self):
        current_datetime = timezone.now()
        return (
            self.date == current_datetime.date()
            and self.time >= current_datetime.time()
        )

    @property
    def reservation_status(self):
        from hita_arab_festival.models.Reservation import ReservationStatus

        if self.reserved_seats >= self.allowed_seats + self.allowed_waiting:
            return None
        elif self.reserved_seats >= self.allowed_seats:
            return ReservationStatus.WAITING_LIST
        else:
            return ReservationStatus.CONFIRMED

    @property
    def is_open_for_reservation(self):
        from hita_arab_festival.models.Reservation import ReservationStatus

        current_datetime = timezone.now()
        if self.date != current_datetime.date():
            return ReservationStatus.CLOSED
        if self.time < current_datetime.time():
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
        current_datetime = timezone.now()
        if self.date > current_datetime.date():
            return False
        if self.date == current_datetime.date() and self.time < current_datetime.time():
            return False
        return True

    def __str__(self):
        return f'{self.name}'
