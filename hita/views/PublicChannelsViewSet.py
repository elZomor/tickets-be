from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from hita.models import PublicChannel, PublicChannelTypes
from hita.permissions import IsHITAMemberPermission
from hita.serializers import PublicChannelViewSerializer, PublicChannelCreateSerializer
from utils.Response import get_successful_creation_response, get_successful_response
from utils.code_utils import authorize_performer_data, get_hita_member_from_request


class PublicChannelsViewSet(viewsets.ModelViewSet):
    queryset = PublicChannel.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = PublicChannelCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return get_successful_creation_response(message='Channel created successfully!')

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        channels = performer.public_channel_list.all()
        serializer = PublicChannelViewSerializer(channels, many=True)
        return get_successful_response(data=serializer.data)

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return get_successful_response(message='Channel updated successfully!')

    @action(detail=False, methods=['GET'], url_path='types')
    def get_public_channel_types(self, request, *args, **kwargs):
        queryset = [label for label, _ in PublicChannelTypes.choices]
        return get_successful_response(data=queryset)

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
