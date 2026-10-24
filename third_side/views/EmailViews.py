from rest_framework import serializers, status
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import EmailAudience, EmailStatus, OutgoingEmail
from third_side.permissions import RequirePerm
from third_side.services import mail

MAX_RECIPIENTS = 50


class OutgoingEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutgoingEmail
        fields = [
            'id',
            'from_email',
            'to',
            'cc',
            'subject',
            'direction',
            'audience',
            'status',
            'error',
            'created_at',
        ]


class SendEmailSerializer(serializers.Serializer):
    to = serializers.ListField(child=serializers.EmailField(), required=False)
    cc = serializers.ListField(child=serializers.EmailField(), required=False)
    subject = serializers.CharField(max_length=255)
    direction = serializers.ChoiceField(choices=['rtl', 'ltr'], default='rtl')
    doc = serializers.JSONField(required=False, allow_null=True)
    html = serializers.CharField()
    audience = serializers.ChoiceField(
        choices=EmailAudience.choices, default=EmailAudience.DIRECT
    )
    # A test goes to the sender only and is not kept in the history.
    test = serializers.BooleanField(default=False)
    signature = serializers.BooleanField(default=True)

    def validate_audience(self, value):
        if value == EmailAudience.SUBSCRIBERS:
            raise serializers.ValidationError(
                'Sending to subscribers is not available yet'
            )
        return value

    def validate(self, data):
        to = list(dict.fromkeys(e.lower() for e in data.get('to', [])))
        cc = [
            e
            for e in dict.fromkeys(e.lower() for e in data.get('cc', []))
            if e not in to
        ]
        if not data['test'] and not to:
            raise serializers.ValidationError({'to': 'At least one recipient'})
        if len(to) + len(cc) > MAX_RECIPIENTS:
            raise serializers.ValidationError(
                {'to': f'At most {MAX_RECIPIENTS} recipients per email'}
            )
        data['to'], data['cc'] = to, cc
        return data


def render(request, data):
    """The full email as sent: frame, body and (unless switched off) signature."""
    direction = data['direction']
    signature = (
        mail.signature_html(request.user, direction, request)
        if data['signature']
        else ''
    )
    return mail.render_email(data['html'], direction, signature)


class PreviewSerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=['rtl', 'ltr'], default='rtl')
    html = serializers.CharField(allow_blank=True, default='')
    signature = serializers.BooleanField(default=True)


class EmailPreviewView(APIView):
    """POST emails/preview: the email exactly as it would be sent (nothing sent)."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    required_perms = {'post': 'add_outgoingemail'}
    serializer_class = PreviewSerializer

    def post(self, request):
        serializer = PreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'html': render(request, serializer.validated_data)})


def _text_map(value, field):
    """{ar, en} with trimmed strings; other keys dropped."""
    if value in (None, ''):
        return {}
    if not isinstance(value, dict):
        raise serializers.ValidationError({field: 'Expected {ar, en}'})
    out = {}
    for lang in ('ar', 'en'):
        text = value.get(lang) or ''
        if not isinstance(text, str) or len(text) > 120:
            raise serializers.ValidationError(
                {field: f'{lang}: at most 120 characters'}
            )
        if text.strip():
            out[lang] = text.strip()
    return out


class SignatureSerializer(serializers.Serializer):
    name = serializers.JSONField(required=False)
    title = serializers.JSONField(required=False)
    phone = serializers.CharField(max_length=40, allow_blank=True, default='')
    show_photo = serializers.BooleanField(default=True)
    show_social = serializers.BooleanField(default=True)

    def validate(self, data):
        data['name'] = _text_map(data.get('name'), 'name')
        data['title'] = _text_map(data.get('title'), 'title')
        data['phone'] = data['phone'].strip()
        return data


class SignatureView(APIView):
    """GET/PUT profile/me/signature: the signed-in editor's email signature."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    required_perms = {'get': 'add_outgoingemail', 'put': 'add_outgoingemail'}
    serializer_class = SignatureSerializer
    throttle_scope = 'third_side_write'

    def get(self, request):
        return Response(SignatureSerializer(request.user.signature or {}).data)

    def put(self, request):
        serializer = SignatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.signature = serializer.validated_data
        request.user.save(update_fields=['signature'])
        return Response(serializer.validated_data)


class EmailView(ListCreateAPIView):
    """Editors send email from their own @third-side.org address via Brevo.

    GET emails: sent history (newest first). POST emails: send one.
    """

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    required_perms = {'get': 'view_outgoingemail', 'post': 'add_outgoingemail'}
    serializer_class = OutgoingEmailSerializer
    throttle_scope = 'third_side_write'

    def get_queryset(self):
        return OutgoingEmail.objects.all()

    def create(self, request, *args, **kwargs):
        user = request.user
        if not mail.is_on_mail_domain(user.email):
            return Response(
                {'detail': 'Your account email is not on the site mail domain'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        html = render(request, data)

        if data['test']:
            try:
                mail.send(
                    user.email,
                    user.display_name,
                    [user.email],
                    f'[Test] {data["subject"]}',
                    html,
                )
            except mail.MailError as exc:
                return Response(
                    {'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY
                )
            return Response({'ok': True})

        email = OutgoingEmail(
            sender=user,
            from_email=user.email,
            to=data['to'],
            cc=data['cc'],
            subject=data['subject'],
            direction=data['direction'],
            doc=data.get('doc'),
            html=html,
            audience=data['audience'],
        )
        try:
            email.provider_message_id = mail.send(
                user.email,
                user.display_name,
                data['to'],
                data['subject'],
                html,
                cc=data['cc'],
            )
            email.status = EmailStatus.SENT
        except mail.MailError as exc:
            email.status = EmailStatus.FAILED
            email.error = str(exc)
        email.save()
        body = OutgoingEmailSerializer(email).data
        if email.status == EmailStatus.FAILED:
            return Response(body, status=status.HTTP_502_BAD_GATEWAY)
        return Response(body, status=status.HTTP_201_CREATED)
