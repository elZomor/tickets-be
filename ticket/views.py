import os

from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from django.utils.translation import gettext as _

from ticket.models import Reservation, Performance
from ticket.serializer import ReservationRequestSerializer, ReservationSerializer
from utils.email_utils import send_email
from utils.qr_utils import generate_qr


class TicketReservationView(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = ReservationRequestSerializer
    queryset = Reservation.objects.all()

    def create(self, request, *args, **kwargs):
        request_serializer = self.get_serializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        reservation = Reservation.objects.create(**request_serializer.validated_data)
        qr_path = generate_qr(f"http://localhost:8005/tickets/reservation/{reservation.reservation_hash}")
        send_email(play_name=reservation.performance.name('en'),
                   to_email=request_serializer.validated_data.get('email'),
                   qr_path=qr_path)
        try:
            os.remove(qr_path)
        except OSError:
            pass
        return Response(data={"status": _("SUCCESS"), "data": _("Ticket has been reserved successfully!")},
                        status=status.HTTP_201_CREATED)
