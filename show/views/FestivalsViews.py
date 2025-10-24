import os
from datetime import date as date_cls, time as time_cls
from io import BytesIO

import requests
from PIL import Image
from django.conf import settings
from django.db.models import DateField, OuterRef, Prefetch, Subquery, TimeField, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from config.constants import BE_URL, SHOW_NIGHT_FE_URL
from config.pagination import CustomPagination
from show.models import Festival, Show, ShowDate
from show.models.Show import ShowStatus
from show.serializer import FestivalViewSerializer


class FestivalViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    serializer_class = FestivalViewSerializer
    queryset = Festival.objects.all().order_by('-start_date', '-end_date')
    pagination_class = CustomPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        latest_date_sq = (
            ShowDate.objects.filter(show=OuterRef('pk'))
            .order_by('-date', '-time')
            .values('date')[:1]
        )
        latest_time_on_latest_sq = (
            ShowDate.objects.filter(
                show=OuterRef('pk'),
                date=Subquery(latest_date_sq),
            )
            .order_by('-time')
            .values('time')[:1]
        )
        shows_prefetch = Prefetch(
            'shows',
            queryset=Show.objects.filter(status=ShowStatus.APPROVED.value)
            .select_related('festival')
            .annotate(
                latest_date=Coalesce(
                    Subquery(latest_date_sq, output_field=DateField()),
                    Value(date_cls.min, output_field=DateField()),
                ),
                latest_time=Coalesce(
                    Subquery(latest_time_on_latest_sq, output_field=TimeField()),
                    Value(time_cls.min, output_field=TimeField()),
                ),
            )
            .prefetch_related(
                'tags',
                Prefetch(
                    'dates',
                    queryset=ShowDate.objects.select_related('theater').only(
                        'id',
                        'show_id',
                        'date',
                        'time',
                        'theater_id',
                        'theater__name',
                        'theater__location',
                    ),
                ),
            )
            .order_by('-latest_date', '-latest_time'),
            to_attr='prefetched_shows',
        )
        return (
            Festival.objects.all()
            .order_by('-start_date', '-end_date')
            .prefetch_related(shows_prefetch)
        )

    def get_authenticators(self):
        if self.request.method == 'GET':
            return []
        return super().get_authenticators()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        date_param = request.query_params.get('date')
        if date_param:
            queryset = queryset.filter(
                start_date__lte=date_param, end_date__gte=date_param
            )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        return Response('Create Festival', status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['GET'], url_path='share')
    def profile_meta(self, request, pk=None):
        festival: Festival = get_object_or_404(Festival, id=pk)
        frontend_url = f"{SHOW_NIGHT_FE_URL}/festivals/{pk}"

        padded_image_data = (
            f"https://media.play-cast.com/{festival.logo.name}?w=1200&h=630&fit=pad&bg=ffffff&q=75&fmt=auto"
            if festival.logo
            else None
        )

        html_content = f"""<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta property="og:title" content="المهرجان المسرحي: {festival.name}">
                    <meta property="og:image" content="{padded_image_data}">
                    <meta property="og:image:secure_url" content="{padded_image_data}">
                    <meta property="og:image:width" content="1200">
                    <meta property="og:image:height" content="630">
                    <meta property="og:image:type" content="image/jpeg">
                    <meta property="og:image:alt" content="Poster of the festival {festival.name}">
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
