from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from hita.models import Gallery
from hita.permissions import IsHITAMemberPermission
from hita.serializers import GalleryCreateSerializer, GalleryViewSerializer
from utils.code_utils import get_hita_member_from_request, authorize_performer_data


class GalleryViewSet(viewsets.ModelViewSet):
    queryset = Gallery.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = GalleryCreateSerializer

    @get_hita_member_from_request
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance: Gallery = serializer.save()
        if instance.is_profile_picture:
            instance.performer.get_gallery(request.user).exclude(id=instance.id).update(
                is_profile_picture=False
            )
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'Image uploaded successfully!',
            },
        )

    @get_hita_member_from_request
    def list(self, request, performer, *args, **kwargs):
        gallery = performer.get_gallery(request.user).all()
        serializer = GalleryViewSerializer(gallery, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Gallery retrieved successfully!',
                'data': serializer.data,
            },
        )

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        instance: Gallery = self.get_object()
        if instance.is_profile_picture:
            instance.performer.get_gallery(request.user).exclude(id=instance.id).update(
                is_profile_picture=False
            )
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Gallery updated successfully!',
            },
        )

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
