from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from django.utils.translation import gettext as _

from ticket.models import Reservation, Performance
from ticket.serializer import ReservationRequestSerializer, ReservationSerializer


class TicketReservationView(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = ReservationRequestSerializer
    queryset = Reservation.objects.all()

    def create(self, request, *args, **kwargs):
        request_serializer = self.get_serializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        Reservation.objects.create(**request_serializer.validated_data)
        return Response(data={"status": _("SUCCESS"), "data": _("Ticket has been reserved successfully!")},
                        status=status.HTTP_201_CREATED)
