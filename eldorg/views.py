from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from config.pagination import CustomPagination
from eldorg.models import Script, ScriptStatus
from eldorg.serializers import ScriptSerializer


class ScriptViewSet(mixins.ListModelMixin, GenericViewSet):
    model = Script
    queryset = Script.objects.filter(status=ScriptStatus.APPROVED).order_by(
        '-created_at'
    )
    serializer_class = ScriptSerializer
    pagination_class = CustomPagination
