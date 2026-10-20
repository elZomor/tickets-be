from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import ActivityLog
from third_side.permissions import IsEditor
from third_side.serializers import (
    ActivityLogDetailSerializer,
    ActivityLogListSerializer,
)


class ActivityLogViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    """Editors read the activity log (newest first). Nobody writes it here.

    Filters: ?actor=<user id> ?action= ?object_type= ?object_id=
    ?date_from=YYYY-MM-DD ?date_to=YYYY-MM-DD ?search=<text in the object name
    or actor>. The list leaves out the before/after values; the detail has them.
    """

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, IsEditor]
    queryset = ActivityLog.objects.order_by('-created_at', '-id')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ActivityLogDetailSerializer
        return ActivityLogListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != 'list':
            return queryset
        params = self.request.query_params
        for name in ('actor', 'action', 'object_type', 'object_id'):
            value = params.get(name)
            if not value:
                continue
            numeric = name in ('actor', 'object_id')
            if numeric and not value.isdigit():
                return queryset.none()
            queryset = queryset.filter(
                **{'actor_id' if name == 'actor' else name: value}
            )
        date_from = parse_date(params.get('date_from') or '')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        date_to = parse_date(params.get('date_to') or '')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        term = params.get('search')
        if term:
            queryset = queryset.filter(
                Q(object_repr__icontains=term)
                | Q(actor_name__icontains=term)
                | Q(actor_email__icontains=term)
            )
        return queryset
