from rest_framework import mixins
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from third_side.models import Critic
from third_side.permissions import IsEditor
from third_side.serializers import CriticSerializer


class CriticViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = CriticSerializer
    queryset = Critic.objects.order_by('name', 'id')

    def get_authenticators(self):
        if getattr(self.request, 'method', None) == 'GET':
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if getattr(self.request, 'method', None) == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsEditor()]
