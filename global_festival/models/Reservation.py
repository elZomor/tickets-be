from django.db import models


class ReservationStatus(models.TextChoices):
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    WAITING_LIST = 'WAITING_LIST', 'Waiting List'
    CLOSED = 'CLOSED', 'Closed'
    OPEN_FOR_RESERVATION = 'OPEN_FOR_RESERVATION', 'Open For Reservation'
    OPEN_FOR_WAITING_LIST = 'OPEN_FOR_WAITING_LIST', 'Open For Waiting List'
    COMPLETE = 'COMPLETE', 'Complete'


class Reservation(models.Model):
    show = models.ForeignKey(
        to='global_festival.Show',
        on_delete=models.CASCADE,
        related_query_name='reservations',
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    status = models.CharField(max_length=20)
    reservation_number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    has_attended = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        return f'{self.show.name}: {self.reservation_number} - {self.name}'
