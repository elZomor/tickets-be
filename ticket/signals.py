from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Reservation, Performance


@receiver(post_save, sender=Reservation)
def update_model2(sender, instance, created, **kwargs):
    if not created: return
    instance.performance.reserved_seats =  instance.performance.reserved_seats + 1
    instance.performance.save()