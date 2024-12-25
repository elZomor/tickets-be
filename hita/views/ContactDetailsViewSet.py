from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from hita.models import ContactDetail
from hita.permissions import IsHITAMemberPermission
from hita.serializers import (
    ContactDetailsViewSerializer,
    ContactDetailsCreateSerializer,
)
from utils.Response import get_successful_creation_response, get_successful_response
from utils.code_utils import get_hita_member_from_request, authorize_performer_data


class ContactDetailsViewSet(viewsets.ModelViewSet):
    queryset = ContactDetail.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = ContactDetailsCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return get_successful_creation_response(message='Contact Detail created successfully!')

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        contact_details = performer.get_contact_details(request.user).all()
        serializer = ContactDetailsViewSerializer(contact_details, many=True)
        return get_successful_response(data=serializer.data)

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return get_successful_response(message='Contact Detail updated successfully!')

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
