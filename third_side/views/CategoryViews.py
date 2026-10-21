from django.db.models import ProtectedError
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.views.audit_mixin import AuditedMixin
from third_side.models import Category, NavGroup, Tag
from third_side.permissions import IsEditor
from third_side.read_serializers import (
    CategoryReadSerializer,
    NavGroupSerializer,
    TagSerializer,
)
from third_side.serializers import TagWriteSerializer
from third_side.site_serializers import (
    CategoryWriteSerializer,
    NavGroupWriteSerializer,
)


class _EditableSectionViewSet(
    AuditedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """Public localized reads; editors write, and read one row through
    GET <id>/doc in the shape the admin form edits (every locale)."""

    authentication_classes = [ThirdSideJWTAuthentication]
    read_serializer_class = None
    write_serializer_class = None

    def _is_public_read(self):
        # self.action is set after the authenticators are picked: use the route.
        if getattr(self.request, 'method', None) != 'GET':
            return False
        return getattr(self, 'action_map', {}).get('get') != 'doc'

    def get_serializer_class(self):
        if self._is_public_read():
            return self.read_serializer_class
        return self.write_serializer_class

    def get_authenticators(self):
        if self._is_public_read():
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self._is_public_read():
            return [AllowAny()]
        return [IsAuthenticated(), IsEditor()]

    @action(detail=True, methods=['get'])
    def doc(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)


class CategoryViewSet(_EditableSectionViewSet):
    queryset = Category.objects.select_related('group').order_by('order', 'id')
    read_serializer_class = CategoryReadSerializer
    write_serializer_class = CategoryWriteSerializer

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'This category still has articles. Move them first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NavGroupViewSet(_EditableSectionViewSet):
    """Header groups. Deleting one leaves its categories ungrouped."""

    queryset = NavGroup.objects.prefetch_related('categories').order_by('order', 'id')
    read_serializer_class = NavGroupSerializer
    write_serializer_class = NavGroupWriteSerializer


class _PublicReadViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []


class TagViewSet(AuditedMixin, mixins.CreateModelMixin, _PublicReadViewSet):
    """Anyone reads the tags; editors create new ones (POST {name: {ar, en, ro}})."""

    queryset = Tag.objects.order_by('slug')

    def get_serializer_class(self):
        if getattr(self.request, 'method', None) == 'GET':
            return TagSerializer
        return TagWriteSerializer

    def get_authenticators(self):
        if getattr(self.request, 'method', None) == 'GET':
            return []
        return [ThirdSideJWTAuthentication()]

    def get_permissions(self):
        if getattr(self.request, 'method', None) == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsEditor()]
