from rest_framework import viewsets

from hita.models import Gallery
from hita.permissions import IsHITAMemberPermission
from hita.serializers import GalleryCreateSerializer, GalleryViewSerializer
from utils.Response import (
    get_successful_creation_response,
    get_successful_response,
    get_bad_request_response,
)
from utils.code_utils import get_hita_member_from_request, authorize_performer_data


class GalleryViewSet(viewsets.ModelViewSet):
    queryset = Gallery.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = GalleryCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance: Gallery = serializer.save()
            if instance.is_profile_picture:
                instance.performer.get_gallery(request.user).exclude(
                    id=instance.id
                ).update(is_profile_picture=False)
            return get_successful_creation_response(
                message='Image uploaded successfully!'
            )
        except Exception as e:
            return get_bad_request_response(message=str(e))

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        gallery = performer.get_gallery(request.user).all()
        serializer = GalleryViewSerializer(gallery, many=True)
        return get_successful_response(data=serializer.data)

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        instance: Gallery = self.get_object()
        if instance.is_profile_picture:
            instance.performer.get_gallery(request.user).exclude(id=instance.id).update(
                is_profile_picture=False
            )
        return get_successful_response(message='Gallery updated successfully!')

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
