import os
from io import BytesIO

import requests
from PIL import Image
from django.conf import settings
from django.db.models import Max, Min
from django.http import HttpResponse
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from config.constants import BE_URL, SHOW_NIGHT_FE_URL
from config.pagination import CustomPagination
from show.models import Show
from show.models.Show import ShowStatus
from show.serializer import ShowViewSerializer


class ShowViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    serializer_class = ShowViewSerializer
    queryset = Show.objects.filter(status=ShowStatus.APPROVED.value)
    pagination_class = CustomPagination
    permission_classes = [AllowAny]

    def get_authenticators(self):
        if self.request.method == 'GET':
            return []
        return super().get_authenticators()

    def list(self, request, *args, **kwargs):
        queryset = (
            self.get_queryset()
            .annotate(latest_date=Max('dates__date'), earliest_time=Min('dates__time'))
            .order_by('-latest_date', 'earliest_time')
        )
        date = request.query_params.get('date')
        if date:
            queryset = (
                self.get_queryset()
                .filter(dates__date=date)
                .order_by('dates__time')
                .distinct()
            )
        serializer = ShowViewSerializer(queryset, many=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        return Response('Create Show', status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['GET'], url_path='share')
    def profile_meta(self, request, pk=None):
        show: Show = get_object_or_404(Show, id=pk)
        show_logo_url = f"{BE_URL}/media/{show.poster}"
        frontend_url = f"{SHOW_NIGHT_FE_URL}/show/{pk}"

        padded_image_data = self.resize_and_pad_image(show_logo_url, is_local=True)

        html_content = f"""<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta property="og:title" content="العرض المسرحي: {show.name}">
                <meta property="og:image" content="{padded_image_data}">
                <meta property="og:image:secure_url" content="{padded_image_data}">
                <meta property="og:image:width" content="1200">
                <meta property="og:image:height" content="630">
                <meta property="og:image:type" content="image/jpeg">
                <meta property="og:image:alt" content="Poster of the play {show.name}">
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

    @staticmethod
    def resize_and_pad_image(image_url, is_local, target_width=1200, target_height=630):
        """
        If the image is local, load it from MEDIA_ROOT instead of fetching via HTTP.
        Resizes while maintaining aspect ratio and adds white padding to 1200x630 px.
        Returns a base64-encoded image.
        """
        image_path = image_url.split("media/", 1)[-1]
        if os.path.exists(f'resized/{image_path}'):
            return f"{BE_URL}/media/resized/{image_path}"
        image = None

        # Check if image is hosted or local
        if not is_local:  # Remote image
            try:
                response = requests.get(image_url, timeout=5)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            except requests.RequestException:
                return image_url  # Return original if request fails
        else:  # Local file (Django MEDIA_ROOT)
            local_path = os.path.join(settings.MEDIA_ROOT, image_path)
            if os.path.exists(local_path):
                image = Image.open(local_path)

        if image is None:
            return image_url  # Fallback to original image

        # Convert to RGB (fixes transparency issues with PNGs)
        image = image.convert("RGB")

        # Resize while maintaining aspect ratio
        image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

        # Create a white background canvas
        new_image = Image.new("RGB", (target_width, target_height), (255, 255, 255))

        # Center the resized image on the white background
        x_offset = (target_width - image.width) // 2
        y_offset = (target_height - image.height) // 2
        new_image.paste(image, (x_offset, y_offset))

        # Save the resized image temporarily
        resized_filename = f"resized/{image_path}"
        resized_path = os.path.join(settings.MEDIA_ROOT, resized_filename)
        os.makedirs(os.path.dirname(resized_path), exist_ok=True)
        new_image.save(resized_path, format="JPEG")

        # Return the new public image URL
        return f"{BE_URL}/media/{resized_filename}"
