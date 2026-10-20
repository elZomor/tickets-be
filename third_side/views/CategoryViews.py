from rest_framework import mixins
from rest_framework.permissions import AllowAny, IsAuthenticated
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
from third_side.serializers import CategorySerializer


class CategoryViewSet(
    AuditedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    authentication_classes = [ThirdSideJWTAuthentication]
    queryset = Category.objects.select_related('group').order_by('order', 'id')

    def get_serializer_class(self):
        if getattr(self.request, 'method', None) == 'GET':
            return CategoryReadSerializer
        return CategorySerializer

    def get_authenticators(self):
        if getattr(self.request, 'method', None) == 'GET':
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if getattr(self.request, 'method', None) == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsEditor()]


class _PublicReadViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []


class NavGroupViewSet(_PublicReadViewSet):
    serializer_class = NavGroupSerializer
    queryset = NavGroup.objects.prefetch_related('categories').order_by('order', 'id')


class TagViewSet(_PublicReadViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.order_by('slug')
