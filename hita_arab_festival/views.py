from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404

from config.constants import HITA_AF_FE_URL
from hita_arab_festival.models import Show, Reservation
from hita_arab_festival.models.Article import Article
from hita_arab_festival.models.Comment import Comment, CommentStatus
from hita_arab_festival.models.Festival import ArabFestival
from hita_arab_festival.serializers import (
    ArabFestivalSerializer,
    ShowSerializer,
    ArticleSerializer,
    CommentSerializer,
)
from utils.Response import (
    get_not_found_response,
    get_successful_response,
    get_successful_creation_response,
    get_bad_request_response,
)


def get_html_for_og(url, pk, file, content, object_name):
    frontend_url = f"{HITA_AF_FE_URL}/{url}/{pk}"

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


class ArabFestivalViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    serializer_class = ArabFestivalSerializer
    queryset = ArabFestival.objects.all()

    @action(detail=True, methods=['GET'], url_path='share')
    def profile_meta(self, request, pk=None):
        festival = get_object_or_404(ArabFestival, id=pk)
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

    def get_queryset(self):
        queryset = super().get_queryset()
        festival_id = self.request.query_params.get('festival')
        if festival_id:
            queryset = queryset.filter(festival__pk=festival_id)
        return queryset

    @action(url_path='reserve', detail=True, methods=["POST"])
    def reserve(self, request, pk, *args, **kwargs):
        data = request.data
        show = Show.objects.filter(pk=pk).last()
        if not show:
            return get_not_found_response(message='NO_SHOW')
        if not show.reservation_status:
            return get_successful_response(message='NO_SEATS')
        try:
            with transaction.atomic():
                selected_show = Show.objects.select_for_update().get(pk=pk)

                previous_reservation = Reservation.objects.filter(
                    email=data.get('email'), show=selected_show
                ).last()
                if previous_reservation:
                    return get_successful_response(message='DUPLICATE_MAIL')

                selected_reservation_status = selected_show.reservation_status
                if not selected_reservation_status:
                    return get_successful_response(message='NO_SEATS')
                selected_show.reserved_seats += 1
                selected_show.save(update_fields=['reserved_seats'])

                reservation = Reservation.objects.create(
                    show=selected_show,
                    name=data.get('name'),
                    email=data.get('email'),
                    reservation_number=selected_show.reserved_seats,
                    status=selected_reservation_status,
                )
            # send_hita_arab_ticket_confirmation_email.delay(
            #     to_email=data.get('email'),
            #     name=data.get('name'),
            #     show_name=show.name,
            #     reservation_number=reservation.reservation_number,
            #     show_date=show.date,
            #     show_time=show.name,
            #     show_venue=show.venue_name,
            # )
            return get_successful_creation_response(
                data={
                    'id': reservation.id,
                    'reservation_number': reservation.reservation_number,
                    'reservation_status': reservation.status,
                    'name': reservation.name,
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

    @action(detail=True, methods=['GET'], url_path='share')
    def profile_meta(self, request, pk=None):
        show = get_object_or_404(Show, id=pk)
        html_content = get_html_for_og(
            'shows', pk, show.poster, f"العرض المسرحي: {show.name}", show.name
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
