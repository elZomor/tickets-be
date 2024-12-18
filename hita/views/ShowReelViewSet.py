import os

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.storages import get_s3_object
from hita.Exceptions import ResourceNotFound
from hita.models import ShowReel
from hita.permissions import IsHITAMemberPermission
from hita.serializers import ShowReelCreateSerializer, ShowReelViewSerializer
from utils.code_utils import get_hita_member_from_request


class ShowReelViewSet(viewsets.ModelViewSet):
    queryset = ShowReel.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = ShowReelCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'ShowReel uploaded successfully!',
            },
        )

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        show_reel = performer.show_reel.all()
        serializer = ShowReelViewSerializer(show_reel, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'ShowReel retrieved successfully!',
                'data': serializer.data,
            },
        )

    def update(self, request, *args, **kwargs):
        return Response(
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            data={
                'status': 'FAILED',
                'message': 'Not Allowed!',
            },
        )

    @action(detail=False, methods=['delete'], url_path='delete')
    @get_hita_member_from_request
    def delete_show_reel(self, request, performer, *args, **kwargs):
        performer.show_reel.delete()
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'ShowReel deleted successfully!',
            },
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
