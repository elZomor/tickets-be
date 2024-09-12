from rest_framework import serializers

from ticket.models import Reservation, Performance, Theater
from django.utils.translation import gettext as _


class ReservationRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    performance = serializers.CharField(max_length=100, required=True)

    def validate_performance(self, performance_name):
        performance: Performance = Performance.objects.filter(
            name__en=performance_name
        ).first()
        if not performance:
            raise serializers.ValidationError(_("Performance does not exist."))
        if performance.remaining_seats == 0:
            raise serializers.ValidationError(_("Sorry, there is no available seats."))
        return performance

    def validate_email(self, email):
        if Reservation.objects.filter(
            email=email, performance__name__en=self.initial_data.get('performance')
        ).exists():
            raise serializers.ValidationError(_("You have already booked a ticket."))
        return email


class ReservationSerializer(serializers.Serializer):
    hash = serializers.CharField(max_length=100, required=True)

    def validate_hash(self, hash):
        if hash is None:
            raise serializers.ValidationError(_("Hash cannot be empty."))
        reservation = Reservation.objects.filter(reservation_hash=hash).last()
        if not reservation:
            raise serializers.ValidationError(_("Reservation does not exist."))
        if reservation.guest_arrived:
            raise serializers.ValidationError(_("Ticket has been already used."))
        if not reservation.performance.is_open:
            raise serializers.ValidationError(_("Performance has been already closed."))
        return hash


class TheaterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theater
        fields = '__all__'


class PerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performance
        fields = '__all__'

    remaining_seats = serializers.SerializerMethodField()

    def get_remaining_seats(self, obj):
        return obj.remaining_seats
