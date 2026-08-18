from django.conf import settings
from django.db import models
from django.db.models import Q

RESERVABLE_ROWS = {
    'G': 22, 'H': 22, 'I': 24, 'J': 24, 'K': 26, 'L': 22,
}


def is_valid_seat(seat: str) -> bool:
    """Validate that a seat ID is in rows G–L and within bounds."""
    if not seat or len(seat) < 2:
        return False
    row = seat[0].upper()
    if row not in RESERVABLE_ROWS:
        return False
    try:
        num = int(seat[1:])
    except ValueError:
        return False
    return 1 <= num <= RESERVABLE_ROWS[row]


class ReservationStatus(models.TextChoices):
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    WAITING_LIST = 'WAITING_LIST', 'Waiting List'
    CLOSED = 'CLOSED', 'Closed'
    OPEN_FOR_RESERVATION = 'OPEN_FOR_RESERVATION', 'Open For Reservation'
    OPEN_FOR_WAITING_LIST = 'OPEN_FOR_WAITING_LIST', 'Open For Waiting List'
    COMPLETE = 'COMPLETE', 'Complete'


class Reservation(models.Model):
    show = models.ForeignKey(
        to='alt_spaces_festival.Show',
        on_delete=models.CASCADE,
        related_query_name='reservations',
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    status = models.CharField(max_length=20)
    reservation_number = models.IntegerField()
    seat_number = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    has_attended = models.BooleanField(default=True, null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alt_spaces_festival_reservations',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['show', 'seat_number'],
                condition=Q(seat_number__isnull=False),
                name='alt_spaces_unique_seat_per_show',
            ),
            models.UniqueConstraint(
                fields=['user', 'show'],
                condition=Q(user__isnull=False),
                name='alt_spaces_unique_user_reservation_per_show',
            ),
        ]

    def __str__(self):
        return f'{self.show.name}: {self.reservation_number} - {self.name}'
