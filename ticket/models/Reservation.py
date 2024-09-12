import hashlib
from datetime import datetime

from django.db import models

from ticket.models import Performance


class Reservation(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    performance = models.ForeignKey(to=Performance, on_delete=models.DO_NOTHING)
    reservation_hash = models.CharField(max_length=100, null=True)
    link_delivered = models.BooleanField(default=False)
    guest_arrived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            self.reservation_hash = self.generate_reservation_hash()
        super().save(*args, **kwargs)

    def generate_reservation_hash(self):
        data = f"{self.name}{self.email}{datetime.now()}"
        return hashlib.sha256(data.encode()).hexdigest()
