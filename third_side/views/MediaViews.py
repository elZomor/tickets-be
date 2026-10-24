from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import Media
from third_side.models.ActivityLog import ActivityAction
from third_side.permissions import EmailVerified, has_perm
from third_side.services import audit
from third_side.services.images import image_error
from third_side.services.media_urls import file_url

MAX_BYTES = 10 * 1024 * 1024


def media_payload(media, request):
    """An uploaded image as the editor embeds it (an upload node's `value`)."""
    return {
        'id': media.pk,
        'key': media.file.name,
        'url': file_url(media.file.name, request),
        'alt': media.alt,
        'width': media.width,
        'height': media.height,
        'mimeType': media.mime_type,
        'filesize': media.filesize,
    }


class MediaUploadView(APIView):
    """POST /media (multipart: file, optional alt).

    Editors upload images for article bodies; readers upload the images they
    attach to a submission (then sent as `images` with POST /submissions).
    Returns the media in the shape the editor embeds in an article body
    (an upload node: id, url, alt, width, height, mimeType, filesize).
    """

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, EmailVerified]
    throttle_scope = 'third_side_write'
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get('file')
        error = image_error(upload, MAX_BYTES)
        if error:
            return Response({'file': [error]}, status=status.HTTP_400_BAD_REQUEST)
        media = Media(
            file=upload,
            alt=request.data.get('alt', ''),
            mime_type=upload.content_type,
            filesize=upload.size,
            uploaded_by=request.user,
        )
        with transaction.atomic():
            media.save()
            # The activity log is for staff actions only.
            if has_perm(request.user, 'add_media'):
                audit.record(
                    request,
                    ActivityAction.UPLOAD,
                    media,
                    {},
                    audit.snapshot(media),
                )
        return Response(media_payload(media, request), status=status.HTTP_201_CREATED)
