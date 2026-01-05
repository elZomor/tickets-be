import os

from django.http import StreamingHttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.storages import get_s3_object, generate_presigned_upload_url
from hita.Exceptions import ResourceNotFound
from hita.models import ShowReel
from hita.permissions import IsHITAMemberPermission
from hita.serializers import ShowReelCreateSerializer, ShowReelViewSerializer
from utils.Response import get_successful_creation_response, get_successful_response
from utils.code_utils import get_hita_member_from_request


class ShowReelViewSet(
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ShowReel.objects.all()
    serializer_class = ShowReelCreateSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsHITAMemberPermission()]

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return get_successful_creation_response(
            message='ShowReel uploaded successfully!'
        )

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        show_reel = performer.show_reel.all()
        serializer = ShowReelViewSerializer(show_reel, many=True)
        return get_successful_response(data=serializer.data)

    @action(detail=False, methods=['delete'], url_path='delete')
    @get_hita_member_from_request
    def delete_show_reel(self, request, performer, *args, **kwargs):
        performer.show_reel.delete()
        return get_successful_response(message='ShowReel deleted successfully!')

    @action(detail=False, methods=['post'], url_path='presigned-url')
    @get_hita_member_from_request
    def get_presigned_upload_url(self, request, performer, *args, **kwargs):
        """
        Get a presigned URL for direct S3 upload.
        Request body: { "content_type": "video/mp4", "file_extension": "mp4" }
        """
        content_type = request.data.get('content_type', 'video/mp4')
        file_extension = request.data.get('file_extension', 'mp4')

        result = generate_presigned_upload_url(
            folder='showreels',
            file_extension=file_extension,
            content_type=content_type,
        )

        return get_successful_response(data=result)

    @action(detail=False, methods=['post'], url_path='confirm-upload')
    @get_hita_member_from_request
    def confirm_upload(self, request, performer, *args, **kwargs):
        """
        Confirm the upload after direct S3 upload is complete.
        Request body: { "file_key": "showreels/uuid.mp4" }
        """
        file_key = request.data.get('file_key')
        if not file_key:
            return Response(
                {'error': 'file_key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete existing showreel if exists
        ShowReel.objects.filter(performer=performer).delete()

        # Create new showreel with S3 key
        ShowReel.objects.create(performer=performer, file=file_key)

        return get_successful_creation_response(
            message='ShowReel uploaded successfully!'
        )

    @action(detail=True, methods=['get'], url_path='stream')
    def stream_video(self, request, *args, **kwargs):
        show_reel = self.get_show_reel()
        file_name = show_reel.file.name
        s3_object = get_s3_object(file_name)

        def file_iterator():
            chunk_size = 8192
            file_obj = s3_object['Body']
            while chunk := file_obj.read(chunk_size):
                yield chunk

        response = StreamingHttpResponse(file_iterator(), content_type='video/mp4')
        response['Content-Disposition'] = (
            f'inline; filename="{os.path.basename(file_name)}"'
        )

        return response

    def get_show_reel(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {
            'performer__hita_member__user__username': self.kwargs[lookup_url_kwarg]
        }
        obj = queryset.filter(**filter_kwargs).first()
        if not obj:
            raise ResourceNotFound(
                f'HITAMember profile with username: {self.kwargs[lookup_url_kwarg]} does not exist'
            )
        self.check_object_permissions(self.request, obj)
        return obj
