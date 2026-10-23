from rest_framework import serializers, status
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import EmailAudience, EmailStatus, OutgoingEmail
from third_side.permissions import IsEditor
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


class EmailView(ListCreateAPIView):
    """Editors send email from their own @third-side.org address via Brevo.

    GET emails: sent history (newest first). POST emails: send one.
    """

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, IsEditor]
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
        html = mail.render_email(data['html'], data['direction'])

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
