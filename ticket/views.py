import os

import environ
from django.utils import timezone
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from django.utils.translation import gettext as _

from ticket.models import Reservation, Performance, Theater
from ticket.serializer import (
    ReservationRequestSerializer,
    ReservationSerializer,
    TheaterSerializer,
    PerformanceSerializer,
)
from utils.email_utils import send_email
from utils.qr_utils import generate_qr


class TicketReservationView(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = ReservationRequestSerializer
    queryset = Reservation.objects.all()

    def create(self, request, *args, **kwargs):
        env = environ.Env()
        request_serializer = self.get_serializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        reservation = Reservation.objects.create(**request_serializer.validated_data)
        qr_path = generate_qr(
            f"{env.str('BASE_URL')}/tickets/reservation/confirm?hash={reservation.reservation_hash}"
        )
        send_email(
            play_name=reservation.performance.name.get('en'),
            to_email=request_serializer.validated_data.get('email'),
            qr_path=qr_path,
        )
        try:
            os.remove(qr_path)
        except OSError:
            pass
        reservation.link_delivered = True
        reservation.save()
        return Response(
            data={
                "status": _("SUCCESS"),
                "data": _("Ticket has been reserved successfully!"),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], url_path='confirm')
    def confirm_reservation(self, request, *args, **kwargs):
        serializer = ReservationSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        reservation = Reservation.objects.filter(
            reservation_hash=serializer.validated_data.get('hash')
        ).last()
        reservation.guest_arrived = True
        reservation.save()
        return Response(
            data={"status": _("SUCCESS"), "data": _("Guest has arrived successfully!")},
            status=status.HTTP_201_CREATED,
        )


class TheaterView(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    serializer_class = TheaterSerializer
    queryset = Theater.objects.all()


class PerformanceView(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    serializer_class = PerformanceSerializer
    queryset = Performance.objects.filter(time__date__gt=timezone.now().date())
