from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from hita.models import PublicChannel
from hita.permissions import IsHITAMemberPermission
from hita.serializers import PublicChannelViewSerializer, PublicChannelCreateSerializer
from utils.code_utils import authorize_performer_data, get_hita_member_from_request


class PublicChannelsViewSet(viewsets.ModelViewSet):
    queryset = PublicChannel.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = PublicChannelCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'Channel created successfully!',
            },
        )

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        channels = performer.public_channel_list.all()
        serializer = PublicChannelViewSerializer(channels, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Channel created successfully!',
                'data': serializer.data,
            },
        )

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            status=status.HTTP_200_OK,
            data={'status': 'SUCCESS', 'message': 'Channel updated successfully!'},
        )

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
