from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.models import Article, Comment, Report
from third_side.permissions import IsEditor
from third_side.serializers import ReportSerializer

TARGET_MODELS = {'article': Article, 'comment': Comment}


class ReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    serializer_class = ReportSerializer
    queryset = Report.objects.select_related(
        'content_type', 'reporter', 'reviewed_by'
    ).order_by('-created_at', '-id')
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'review'):
            return [IsAuthenticated(), IsEditor()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_model = TARGET_MODELS[serializer.validated_data['content_type']]
        object_id = serializer.validated_data['object_id']
        get_object_or_404(target_model, pk=object_id)

        report = Report.objects.create(
            reporter=request.user,
            content_type=ContentType.objects.get_for_model(target_model),
            object_id=object_id,
            reason=serializer.validated_data.get('reason', ''),
        )

        response_serializer = self.get_serializer(report)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['PATCH'])
    def review(self, request, pk=None):
        report = get_object_or_404(Report, pk=pk)
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.save(update_fields=['reviewed_by', 'reviewed_at'])

        target = report.content_type.get_object_for_this_type(pk=report.object_id)
        target.is_hidden = False
        target.save(update_fields=['is_hidden'])

        return Response(self.get_serializer(report).data)
