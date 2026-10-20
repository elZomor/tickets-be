from django.db import transaction
from PIL import Image
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import Media
from third_side.models.ActivityLog import ActivityAction
from third_side.permissions import IsEditor
from third_side.services import audit

MAX_BYTES = 10 * 1024 * 1024


class MediaUploadView(APIView):
    """POST /media (multipart: file, optional alt). Editors only.

    Returns the media in the shape the editor embeds in an article body
    (an upload node: id, url, alt, width, height, mimeType, filesize).
    """

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, IsEditor]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response(
                {'file': ['No file was sent.']}, status=status.HTTP_400_BAD_REQUEST
            )
        if not (upload.content_type or '').startswith('image/'):
            return Response(
                {'file': ['Only images can be uploaded.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > MAX_BYTES:
            return Response(
                {'file': ['The image is larger than 10 MB.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            Image.open(upload).verify()  # Pillow must be able to read it.
            upload.seek(0)
        except Exception:
            return Response(
                {'file': ['This is not a valid image.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        media = Media(
            file=upload,
            alt=request.data.get('alt', ''),
            mime_type=upload.content_type,
            filesize=upload.size,
            uploaded_by=request.user,
        )
        with transaction.atomic():
            media.save()
            audit.record(
                request,
                ActivityAction.UPLOAD,
                media,
                {},
                audit.snapshot(media),
            )
        return Response(
            {
                'id': media.pk,
                'key': media.file.name,
                'url': request.build_absolute_uri(media.file.url),
                'alt': media.alt,
                'width': media.width,
                'height': media.height,
                'mimeType': media.mime_type,
                'filesize': media.filesize,
            },
            status=status.HTTP_201_CREATED,
        )
