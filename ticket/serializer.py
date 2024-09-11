from rest_framework import serializers

from ticket.models import Reservation, Performance
from django.utils.translation import gettext as _


class ReservationRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    performance = serializers.CharField(max_length=100, required=True)

    def validate_performance(self, performance_name):
        performance: Performance = Performance.objects.filter(name__en=performance_name).first()
        if not performance:
            raise serializers.ValidationError(_("Performance does not exist."))
        if performance.remaining_seats == 0:
            raise serializers.ValidationError(_("Sorry, there is no available seats."))
        return performance

    def validate_email(self, email):
        if Reservation.objects.filter(email=email, performance__name__en=self.initial_data.get('performance')).exists():
            raise serializers.ValidationError(_("You have already booked a ticket."))
        return email


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['name', 'email', 'performance']