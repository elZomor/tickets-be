from django.db import models

from ticket.models import Theater
from utils.json_utils import default_localized_model


class Performance(models.Model):
    name = models.JSONField(default=default_localized_model)
    link = models.URLField()
    time = models.DateTimeField()
    theater = models.ForeignKey(to=Theater, on_delete=models.DO_NOTHING)
    initial_reserved_seats = models.IntegerField(default=0)
    reserved_seats = models.IntegerField(default=0)

    @property
    def remaining_seats(self):
        return self.theater.capacity - self.initial_reserved_seats - self.reserved_seats

    @property
    def total_attendees(self):
        from ticket.models import Reservation
        return Reservation.objects.filter(performance__pk=self.pk, guest_arrived=True).count()

    def __str__(self):
        return self.name.get('ar', '')
