"""The Third Side Lab: programs, registrations and certificates.

Readers browse programs (public), register or apply (signed in, verified
email), and see their certificates. Staff (model permissions) manage programs,
review registrations, mark attendance, issue certificates and edit the
certificate templates.
"""

from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.lab_serializers import (
    CertificateAdminSerializer,
    CertificateTemplateSerializer,
    CertificateVerifySerializer,
    LabProgramReadSerializer,
    LabProgramWriteSerializer,
    MyCertificateSerializer,
    MyRegistrationSerializer,
    RegistrationAdminSerializer,
)
from third_side.models import (
    Certificate,
    CertificateTemplate,
    LabProgram,
    LabRegistration,
)
from third_side.models.LabRegistration import RegistrationStatus
from third_side.permissions import EmailVerified, RequirePerm, has_perm, model_perms
from third_side.services import certificates, lab
from third_side.views.audit_mixin import AuditedMixin

ANSWER_LIMITS = {'motivation': 2000, 'phone': 40}


class LabProgramViewSet(
    AuditedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """GET lab-programs (?kind=&status=upcoming|past&lang=), by-slug/{slug} in
    any locale. Staff also see drafts and write; {id}/doc is the admin shape.

    {id}/registration: the signed-in reader's own registration (GET), register
    or apply (POST {motivation, phone}), cancel (DELETE).
    """

    authentication_classes = [ThirdSideJWTAuthentication]
    required_perms = {
        **model_perms('labprogram'),
        'issue_certificates': 'add_certificate',
    }
    throttle_scope = 'third_side_read'

    def get_permissions(self):
        if self.action == 'registration':
            if self.request.method == 'POST':
                return [IsAuthenticated(), EmailVerified()]
            return [IsAuthenticated()]
        if self.action in ('list', 'retrieve', 'by_slug'):
            return [AllowAny()]
        return [IsAuthenticated(), RequirePerm()]

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'by_slug'):
            return LabProgramReadSerializer
        return LabProgramWriteSerializer

    def get_throttles(self):
        if self.request.method != 'GET':
            self.throttle_scope = 'third_side_write'
        return super().get_throttles()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['detail'] = self.action in ('retrieve', 'by_slug')
        return context

    def get_queryset(self):
        queryset = LabProgram.objects.all().order_by('-starts_on', '-id')
        staff = has_perm(self.request.user, 'view_labprogram')
        if not staff or self.action in ('by_slug', 'registration'):
            queryset = queryset.filter(is_published=True)
        params = self.request.query_params
        kind = params.get('kind')
        if kind:
            queryset = queryset.filter(kind=kind)
        today = timezone.localdate()
        when = params.get('status')
        if when == 'upcoming':
            queryset = queryset.filter(ends_on__gte=today).order_by('starts_on', 'id')
        elif when == 'past':
            queryset = queryset.filter(ends_on__lt=today)
        return queryset

    def destroy(self, request, *args, **kwargs):
        if self.get_object().certificates.exists():
            return Response(
                {'detail': 'This program has certificates; unpublish it instead.'},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path=r'by-slug/(?P<slug>[^/]+)')
    def by_slug(self, request, slug=None):
        for program in self.get_queryset():
            if slug == program.slug or slug in program.slug_i18n.values():
                return Response(self.get_serializer(program).data)
        raise Http404

    @action(detail=True, methods=['get'])
    def doc(self, request, pk=None):
        return Response(
            LabProgramWriteSerializer(
                self.get_object(), context=self.get_serializer_context()
            ).data
        )

    @action(detail=True, methods=['get', 'post', 'delete'])
    def registration(self, request, pk=None):
        program = self.get_object()
        mine = LabRegistration.objects.filter(
            program=program, user=request.user
        ).first()
        if request.method == 'GET':
            return Response(_my_registration(mine))
        if request.method == 'DELETE':
            if mine is None or mine.status not in lab.LIVE:
                return Response(status=status.HTTP_204_NO_CONTENT)
            lab.cancel(mine)
            mine.refresh_from_db()
            return Response(_my_registration(mine))
        answers = {
            key: str(request.data.get(key) or '').strip()[:limit]
            for key, limit in ANSWER_LIMITS.items()
        }
        if program.registration_mode == 'application' and not answers['motivation']:
            return Response(
                {'motivation': 'Tell us why you want to join.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            registration = lab.register(program, request.user, answers)
        except lab.RegistrationError as error:
            return Response(
                {'detail': 'Registration is not open', 'code': error.code},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(_my_registration(registration), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='issue-certificates')
    def issue_certificates(self, request, pk=None):
        """AR certificates for every attended participant without one
        (or only `registration_ids`)."""
        program = self.get_object()
        ids = request.data.get('registration_ids')
        if ids is not None and not isinstance(ids, list):
            return Response({'registration_ids': 'Expected a list.'}, status=400)
        issued = certificates.issue_arabic(program, request, ids)
        return Response({'issued': len(issued), 'codes': [c.code for c in issued]})


def _my_registration(registration):
    if registration is None:
        return {'status': None}
    return {
        'id': registration.id,
        'status': registration.status,
        'attended': registration.attended,
        'created_at': registration.created_at,
    }


class LabRegistrationViewSet(
    AuditedMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    """Staff: the participants of a program (?program=<id>, &status=).
    PATCH {status, attended, note}; POST bulk {ids, status?, attended?}."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    required_perms = {
        **model_perms('labregistration'),
        'bulk': 'change_labregistration',
    }
    serializer_class = RegistrationAdminSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = LabRegistration.objects.select_related('user').order_by(
            'created_at', 'id'
        )
        params = self.request.query_params
        program = params.get('program')
        if not (program and program.isdigit()):
            return queryset.none() if self.action == 'list' else queryset
        queryset = queryset.filter(program_id=int(program))
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        program = self.request.query_params.get('program')
        if self.action == 'list' and program and program.isdigit():
            context['certificate_codes'] = dict(
                Certificate.objects.filter(
                    program_id=int(program), language='ar'
                ).values_list('user_id', 'code')
            )
        return context

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        ids = request.data.get('ids')
        if not isinstance(ids, list) or not ids:
            return Response({'ids': 'Pick at least one participant.'}, status=400)
        changes = {}
        new_status = request.data.get('status')
        if new_status is not None:
            if new_status not in RegistrationStatus.values:
                return Response({'status': 'Unknown status.'}, status=400)
            changes['status'] = new_status
        if 'attended' in request.data:
            changes['attended'] = bool(request.data['attended'])
        if not changes:
            return Response({'detail': 'Nothing to change.'}, status=400)
        # One save per row so signals (notifications, activity log) fire.
        rows = LabRegistration.objects.filter(pk__in=ids)
        for row in rows:
            for field, value in changes.items():
                setattr(row, field, value)
            row.save(update_fields=[*changes, 'updated_at'])
        return Response({'updated': len(rows)})


class MyLabRegistrationsView(APIView):
    """GET lab-registrations/mine (?lang=): the reader's registrations."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_read'

    def get(self, request):
        rows = (
            LabRegistration.objects.filter(user=request.user)
            .exclude(status=RegistrationStatus.CANCELLED)
            .select_related('program')
            .order_by('-created_at')
        )
        data = MyRegistrationSerializer(
            rows, many=True, context={'request': request}
        ).data
        return Response(data)


class MyCertificatesView(APIView):
    """GET certificates/mine (?lang=): the reader's certificates."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_read'

    def get(self, request):
        rows = (
            Certificate.objects.filter(user=request.user, revoked=False)
            .select_related('program')
            .prefetch_related('translations')
            .order_by('-issued_at')
        )
        data = MyCertificateSerializer(
            rows, many=True, context={'request': request}
        ).data
        return Response(data)


class CertificateEnglishView(APIView):
    """POST certificates/{code}/english {name}: the English version of the
    reader's Arabic certificate, issued at once (201) or held until the
    program has English text (202)."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_write'

    def post(self, request, code):
        certificate = get_object_or_404(
            Certificate, code=code, user=request.user, revoked=False
        )
        name = str(request.data.get('name') or '').strip()[:200]
        if not name:
            return Response({'name': 'Write your name in English.'}, status=400)
        if any('؀' <= ch <= 'ۿ' for ch in name):
            return Response({'name': 'Use Latin letters.'}, status=400)
        try:
            english = certificates.request_english(certificate, name, request)
        except certificates.EnglishUnavailable:
            return Response({'detail': 'Only an Arabic certificate.'}, status=400)
        if english is None:
            return Response({'status': 'waiting'}, status=status.HTTP_202_ACCEPTED)
        return Response(
            {'status': 'issued', 'code': english.code}, status=status.HTTP_201_CREATED
        )


class _PublicCertificate(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'third_side_read'

    @staticmethod
    def find(code):
        return get_object_or_404(
            Certificate.objects.select_related('program', 'template'), code=code.upper()
        )


class CertificateVerifyView(_PublicCertificate):
    """GET certificates/verify/{code} (?lang=): is this certificate real."""

    def get(self, request, code):
        certificate = self.find(code)
        return Response(
            CertificateVerifySerializer(certificate, context={'request': request}).data
        )


class CertificateHtmlView(_PublicCertificate):
    """GET certificates/{code}/html: the rendered certificate document."""

    def get(self, request, code):
        certificate = self.find(code)
        if certificate.revoked:
            raise Http404
        response = HttpResponse(
            certificates.render_certificate(certificate),
            content_type='text/html; charset=utf-8',
        )
        response['Cache-Control'] = 'public, max-age=300'
        return response


class CertificateViewSet(
    AuditedMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    """Staff: issued certificates (?program=, ?waiting=1 for held English
    requests). PATCH {participant_name, revoked}."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    required_perms = model_perms('certificate')
    serializer_class = CertificateAdminSerializer

    def get_queryset(self):
        queryset = Certificate.objects.select_related('user', 'source').order_by(
            '-issued_at', '-id'
        )
        params = self.request.query_params
        program = params.get('program')
        if program and program.isdigit():
            queryset = queryset.filter(program_id=int(program))
        if params.get('waiting'):
            queryset = queryset.exclude(english_name_requested='')
        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(code__iexact=search)
                | Q(participant_name__icontains=search)
                | Q(user__email__icontains=search)
            )
        return queryset


class CertificateTemplateViewSet(AuditedMixin, ModelViewSet):
    """Staff: certificate templates. POST preview {html, language} renders
    with sample values."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    required_perms = {
        **model_perms('certificatetemplate'),
        'preview': 'view_certificatetemplate',
    }
    serializer_class = CertificateTemplateSerializer
    pagination_class = None

    def get_queryset(self):
        if not CertificateTemplate.objects.exists():
            for lang in ('ar', 'en'):
                certificates.ensure_default_template(lang)
        return CertificateTemplate.objects.all()

    @action(detail=False, methods=['post'])
    def preview(self, request):
        from django.template import TemplateSyntaxError

        lang = (
            request.data.get('language')
            if request.data.get('language')
            in (
                'ar',
                'en',
            )
            else 'ar'
        )
        html = request.data.get('html')
        if not isinstance(html, str) or not html.strip():
            html = certificates.ensure_default_template(lang).html
        context = certificates.sample_context(lang)
        program_id = request.data.get('program')
        if str(program_id or '').isdigit():
            program = LabProgram.objects.filter(pk=int(program_id)).first()
            if program is not None:
                context.update(certificates.program_context(program, lang, request))
        try:
            rendered = certificates.render(html, context, 'SAMPLE2345', lang)
        except TemplateSyntaxError as error:
            return Response({'html': f'Template error: {error}'}, status=400)
        return Response({'html': rendered})
