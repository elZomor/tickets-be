from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import Article, Comment, ModerationAction, Report
from third_side.models.ActivityLog import ActivityAction, ActivityObject
from third_side.models.ModerationAction import ModerationActionType
from third_side.permissions import EmailVerified, RequirePerm, has_perm
from third_side.serializers import (
    ReportAdminSerializer,
    ReportSerializer,
    report_target_author,
)
from third_side.services import audit, moderation_mail

TARGET_MODELS = {'article': Article, 'comment': Comment}


class ResolveSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ModerationActionType.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    # Warn / delete / suspend may also hide the content (hide, suspend always do).
    hide_content = serializers.BooleanField(required=False, default=False)
    send_email = serializers.BooleanField(required=False, default=False)
    email_subject = serializers.CharField(required=False, allow_blank=True, max_length=200)
    email_body = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    notify_reporters = serializers.BooleanField(required=False, default=True)


class ReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    serializer_class = ReportSerializer
    authentication_classes = [ThirdSideJWTAuthentication]
    queryset = Report.objects.select_related(
        'content_type', 'reporter', 'reviewed_by'
    ).order_by('-created_at', '-id')
    permission_classes = [IsAuthenticated]
    required_perms = {
        'list': 'view_report',
        'retrieve': 'view_report',
        'review': 'change_report',
        'resolve': 'change_report',
        'warning_template': 'change_report',
    }
    throttle_scope = 'third_side_write'

    def get_permissions(self):
        if self.action in self.required_perms:
            return [IsAuthenticated(), RequirePerm()]
        # Reporting is a reader contribution: unverified accounts are refused.
        return [IsAuthenticated(), EmailVerified()]

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'resolve'):
            return ReportAdminSerializer
        return ReportSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['detail'] = self.action in ('retrieve', 'resolve')
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != 'list':
            return queryset
        params = self.request.query_params
        reviewed = params.get('reviewed')
        if reviewed in ('true', '1'):
            queryset = queryset.filter(reviewed_at__isnull=False)
        elif reviewed in ('false', '0'):
            queryset = queryset.filter(reviewed_at__isnull=True)
        if params.get('content_type') in TARGET_MODELS:
            queryset = queryset.filter(
                content_type=ContentType.objects.get_for_model(
                    TARGET_MODELS[params['content_type']]
                )
            )
        if params.get('reason'):
            queryset = queryset.filter(reason=params['reason'])
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_model = TARGET_MODELS[serializer.validated_data['content_type']]
        object_id = serializer.validated_data['object_id']
        get_object_or_404(target_model, pk=object_id)

        # One report per reader per target: repeating it is a no-op, so a
        # single reader cannot push a target past the auto-hide threshold.
        report, created = Report.objects.get_or_create(
            reporter=request.user,
            content_type=ContentType.objects.get_for_model(target_model),
            object_id=object_id,
            defaults={
                'reason': serializer.validated_data.get('reason', ''),
                'note': serializer.validated_data.get('note') or None,
            },
        )

        response_serializer = self.get_serializer(report)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['GET'], url_path='warning-template')
    def warning_template(self, request, pk=None):
        report = get_object_or_404(Report, pk=pk)
        author = report_target_author(report)
        if author is None:
            return Response({'detail': 'The target has no author'}, status=404)
        return Response(moderation_mail.warning_template(author, report.content_type.model))

    @action(detail=True, methods=['POST'])
    def resolve(self, request, pk=None):
        report = get_object_or_404(Report.objects.select_related('content_type'), pk=pk)
        body = ResolveSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return self._apply(request, report, body.validated_data)

    def _apply(self, request, report, data):
        kind = data['action']
        model = report.content_type.model
        target = report.target
        author = report_target_author(report)

        if kind == ModerationActionType.DELETE:
            needed = 'delete_comment' if model == 'comment' else 'delete_article'
            if not has_perm(request.user, needed):
                return Response({'detail': 'Not allowed to delete this'}, status=403)
        if kind == ModerationActionType.SUSPEND:
            if not has_perm(request.user, 'suspend_user'):
                return Response({'detail': 'Not allowed to suspend users'}, status=403)
            if author is None:
                return Response({'detail': 'The target has no author'}, status=400)
            if author.is_superuser or author.groups.exists():
                return Response({'detail': 'Staff accounts cannot be suspended here'}, status=400)
        if data['send_email']:
            if author is None:
                return Response({'detail': 'The target has no author to email'}, status=400)
            if not (data.get('email_subject') and data.get('email_body')):
                return Response({'detail': 'Email subject and body are required'}, status=400)

        label = f'{model} #{report.object_id}'
        # Every open report on the same target is settled by this one decision.
        open_reports = list(
            Report.objects.filter(
                content_type=report.content_type,
                object_id=report.object_id,
                reviewed_at__isnull=True,
            ).select_related('reporter')
        )

        changes = {}
        with transaction.atomic():
            was_hidden = getattr(target, 'is_hidden', None)
            if target is not None:
                if kind == ModerationActionType.DELETE and model == 'comment':
                    changes['target'] = {'before': label, 'after': None}
                    target.delete()
                    target = None
                else:
                    # Dismiss brings the content back (an auto-hide included);
                    # warn keeps it hidden only when the moderator says so;
                    # articles are never hard-deleted from here, only hidden.
                    new_hidden = {
                        ModerationActionType.DISMISS: False,
                        ModerationActionType.WARN: data['hide_content'],
                    }.get(kind, True)
                    if new_hidden != was_hidden:
                        target.is_hidden = new_hidden
                        target.save(update_fields=['is_hidden'])
                        changes['target_is_hidden'] = {
                            'before': was_hidden,
                            'after': new_hidden,
                        }
            if kind == ModerationActionType.SUSPEND:
                author.is_active = False
                author.save(update_fields=['is_active'])
                changes['author_is_active'] = {'before': True, 'after': False}

            now = timezone.now()
            for item in open_reports:
                item.reviewed_by = request.user
                item.reviewed_at = now
                item.save(update_fields=['reviewed_by', 'reviewed_at'])

            email_sent = False
            if data['send_email']:
                email_sent = moderation_mail.send_warning(
                    author, data['email_subject'], data['email_body']
                )
            record = ModerationAction.objects.create(
                report=report,
                content_type=report.content_type,
                object_id=report.object_id,
                author=author,
                moderator=request.user,
                action=kind,
                note=data.get('note', ''),
                email_sent=email_sent,
            )
            changes['decision'] = {'before': None, 'after': kind}
            audit.write(
                request,
                ActivityAction.REVIEW,
                ActivityObject.REPORT,
                report.pk,
                label,
                changes,
            )

        if data['notify_reporters']:
            seen = set()
            for item in open_reports:
                if item.reporter_id in seen or item.reporter_id == request.user.pk:
                    continue
                seen.add(item.reporter_id)
                moderation_mail.send_reporter_thanks(item.reporter)

        report.refresh_from_db()
        payload = self.get_serializer(report).data
        payload['email_requested'] = data['send_email']
        payload['email_sent'] = record.email_sent
        return Response(payload)

    @action(detail=True, methods=['PATCH'])
    def review(self, request, pk=None):
        """Dismiss: the report was wrong, so the content comes back."""
        report = get_object_or_404(Report.objects.select_related('content_type'), pk=pk)
        return self._apply(
            request,
            report,
            {
                'action': ModerationActionType.DISMISS,
                'note': '',
                'hide_content': False,
                'send_email': False,
                'notify_reporters': False,
            },
        )
