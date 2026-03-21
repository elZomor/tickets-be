from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, mixins, generics
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from config.constants import GLOBAL_FESTIVAL_FE_URL, SEND_EMAIL
from global_festival.models import Show, Reservation
from global_festival.models.Reservation import is_valid_seat, ReservationStatus
from global_festival.models.Article import Article
from global_festival.models.Comment import Comment, CommentStatus
from global_festival.models.Festival import GlobalFestival
from global_festival.serializers import (
    GlobalFestivalSerializer,
    ShowSerializer,
    ArticleSerializer,
    CommentSerializer,
    ReservationSerializer,
    UserReservationSerializer,
)
from utils.Response import (
    get_not_found_response,
    get_successful_response,
    get_successful_creation_response,
    get_bad_request_response,
)
from utils.email_utils import send_global_festival_ticket_confirmation_email


def get_html_for_og(url, pk, file, content, object_name):
    frontend_url = f"{GLOBAL_FESTIVAL_FE_URL}/{url}/{pk}"

    padded_image_data = (
        f"https://media.play-cast.com/{file.name}?w=1200&h=630&fit=pad&bg=ffffff&q=75&fmt=jpg"
        if file
        else None
    )

    html_content = f"""<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta property="og:title" content="{content}">
                    <meta property="og:image" content="{padded_image_data}">
                    <meta property="og:image:secure_url" content="{padded_image_data}">
                    <meta property="og:image:width" content="1200">
                    <meta property="og:image:height" content="630">
                    <meta property="og:image:type" content="image/jpeg">
                    <meta property="og:image:alt" content="Poster of the festival {object_name}">
                    <meta property="og:type" content="profile">
                    <meta property="og:url" content="{frontend_url}">

                    <script>
                            window.location.href = "{frontend_url}";
                    </script>

                    <noscript>
                        <meta http-equiv="refresh" content="3; url={frontend_url}">
                    </noscript>
                </head>
                <body>
                    <p>Redirecting to <a href="{frontend_url}">{frontend_url}</a> in a few seconds...</p>
                </body>
                </html>"""

    return HttpResponse(html_content, content_type="text/html; charset=utf-8")


class GlobalFestivalViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    serializer_class = GlobalFestivalSerializer
    queryset = GlobalFestival.objects.all()

    @action(detail=True, methods=['GET'], url_path='share')
    def profile_meta(self, request, pk=None):
        festival = get_object_or_404(GlobalFestival, id=pk)
        html_content = get_html_for_og(
            'festival', pk, festival.logo, festival.name, festival.name
        )
        return HttpResponse(html_content, content_type="text/html; charset=utf-8")


class ArticleViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    serializer_class = ArticleSerializer
    queryset = Article.objects.all()

    def get_queryset(self):
        article_type = self.request.query_params.get('type')
        return self.queryset.filter(article_type=article_type)


class ShowViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    serializer_class = ShowSerializer
    queryset = Show.objects.all().order_by('date', 'time')

    def get_permissions(self):
        if self.action in ['reserve', 'my_reservation']:
            return [IsAuthenticated()]
        return []

    @action(url_path='seats', detail=True, methods=["GET"])
    def seats(self, request, pk, *args, **kwargs):
        show = Show.objects.filter(pk=pk).last()
        if not show:
            return get_not_found_response(message='NO_SHOW')
        taken = list(
            Reservation.objects
            .filter(show=show, seat_number__isnull=False)
            .values_list('seat_number', flat=True)
        )
        return get_successful_response(data={'taken': taken})

    def get_queryset(self):
        queryset = super().get_queryset()
        festival_id = self.request.query_params.get('festival')
        if festival_id:
            queryset = queryset.filter(festival__pk=festival_id)
        return queryset

    @action(url_path='reserve', detail=True, methods=["POST"])
    def reserve(self, request, pk, *args, **kwargs):
        show = Show.objects.filter(pk=pk).last()
        if not show:
            return get_not_found_response(message='NO_SHOW')
        if not show.reservation_status:
            return get_successful_response(message='NO_SEATS')
        is_waiting_list = show.reservation_status == ReservationStatus.WAITING_LIST
        if not is_waiting_list:
            seat_number = request.data.get('seat_number', '').strip().upper()
            if not is_valid_seat(seat_number):
                return get_bad_request_response(message='INVALID_SEAT')
        previous_reservation = Reservation.objects.filter(
            user=request.user, show=show
        ).last()
        if previous_reservation:
            return get_successful_response(
                data={
                    'id': previous_reservation.id,
                    'name': previous_reservation.name,
                    'reservation_number': previous_reservation.reservation_number,
                    'reservation_status': previous_reservation.status,
                    'seat_number': previous_reservation.seat_number,
                },
                message='DUPLICATE_MAIL',
            )
        try:
            with transaction.atomic():
                selected_show = Show.objects.select_for_update().get(pk=pk)
                selected_reservation_status = selected_show.reservation_status
                if not selected_reservation_status:
                    return get_successful_response(message='NO_SEATS')
                if selected_reservation_status != ReservationStatus.WAITING_LIST:
                    if Reservation.objects.filter(show=selected_show, seat_number=seat_number).exists():
                        return get_bad_request_response(message='SEAT_TAKEN')
                selected_show.reserved_seats += 1
                selected_show.save(update_fields=['reserved_seats'])
                if selected_reservation_status == ReservationStatus.WAITING_LIST:
                    seat_number = str(selected_show.reserved_seats - selected_show.allowed_seats)

            user_name = request.user.get_full_name() or request.user.username
            reservation = Reservation.objects.create(
                show=show,
                name=user_name,
                email=request.user.email,
                user=request.user,
                reservation_number=selected_show.reserved_seats,
                status=selected_reservation_status,
                seat_number=seat_number,
            )
            if SEND_EMAIL:
                send_global_festival_ticket_confirmation_email.delay(
                    to_email=request.user.email,
                    name=user_name,
                    show_name=show.name,
                    reservation_number=reservation.reservation_number,
                    show_date=show.date,
                    show_time=show.time,
                    show_venue=show.venue_name,
                )
            return get_successful_creation_response(
                data={
                    'id': reservation.id,
                    'reservation_number': reservation.reservation_number,
                    'reservation_status': reservation.status,
                    'name': reservation.name,
                    'seat_number': reservation.seat_number,
                },
                message='Reservation created successfully!',
            )
        except Exception as ex:
            return get_bad_request_response(
                data={
                    "status": "UNKNOWN_ERROR",
                    "message": str(ex),
                    "reservation": None,
                }
            )

    @action(url_path='my_reservation', detail=True, methods=["GET"])
    def my_reservation(self, request, pk, *args, **kwargs):
        show = Show.objects.filter(pk=pk).last()
        if not show:
            return get_not_found_response(message='NO_SHOW')
        reservation = Reservation.objects.filter(user=request.user, show=show).last()
        if not reservation:
            return get_not_found_response(message='NO_RESERVATION')
        return get_successful_response(data=ReservationSerializer(reservation).data)

    @action(detail=True, methods=['GET'], url_path='share')
    def profile_meta(self, request, pk=None):
        show = get_object_or_404(Show, id=pk)
        html_content = get_html_for_og(
            'shows', pk, show.poster, f"The Show: {show.name}", show.name
        )
        return HttpResponse(html_content, content_type="text/html; charset=utf-8")


class CommentViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
):
    serializer_class = CommentSerializer
    queryset = Comment.objects.filter(status=CommentStatus.APPROVED)

    def get_queryset(self):
        queryset = super().get_queryset()
        show_id = self.request.query_params.get('show')
        if show_id:
            return queryset.filter(show__pk=show_id)
        return queryset

    def create(self, request, *args, **kwargs):
        data = request.data
        show = Show.objects.filter(pk=data.get('show')).last()
        if not show:
            return get_not_found_response(message='NO_SHOW')
        if not show.is_comment_allowed:
            return get_bad_request_response(message='SHOW_IS_NOT_COMMENT')
        comment = Comment.objects.create(content=data.get('content'), show=show)
        return get_successful_creation_response(
            data={'id': comment.id, 'content': comment.content, 'show': show.name},
            message='Comment has been added successfully!',
        )


class UserReservationsView(generics.ListAPIView):
    serializer_class = UserReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Reservation.objects
            .filter(user=self.request.user)
            .select_related('show', 'show__festival')
            .order_by('-created_at')
        )
