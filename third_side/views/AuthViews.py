import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.auth import issue_tokens, rotate_refresh
from third_side.models import TermsAcceptance, TermsVersion, ThirdSideUser
from third_side.services.mail import send_email

logger = logging.getLogger(__name__)

# The FE serves the reset page at a localized URL segment (accountPaths.ts).
RESET_SEGMENTS = {'ar': 'كلمة-مرور-جديدة', 'en': 'reset-password', 'ro': 'parola-noua'}


class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    # Required once a version is in force, and must be that version: a stale
    # form is refused so nobody accepts text they were not shown.
    accepted_terms_version = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        terms = TermsVersion.current()
        if terms is not None and (
            attrs.get('accepted_terms_version', '').strip() != terms.version
        ):
            raise serializers.ValidationError(
                {
                    'accepted_terms_version': (
                        f'You must accept the current terms (version {terms.version})'
                    )
                }
            )
        attrs['terms'] = terms
        return attrs

    def validate_email(self, value):
        value = value.strip().lower()
        if ThirdSideUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'An account with this email already exists'
            )
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    lang = serializers.ChoiceField(choices=['ar', 'en', 'ro'], default='ar')


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class PublicAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'third_side_auth'


class SignupView(PublicAuthView):
    """Create a reader account and return a token pair."""

    serializer_class = SignupSerializer

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = ThirdSideUser.objects.create_user(
            email=data['email'], password=data['password'], name=data['name'].strip()
        )
        if data['terms'] is not None:
            TermsAcceptance.objects.create(
                user=user,
                terms=data['terms'],
                ip_address=request.META.get('REMOTE_ADDR') or None,
            )
        return Response(issue_tokens(user), status=status.HTTP_201_CREATED)


class LoginView(PublicAuthView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()
        user = ThirdSideUser.objects.filter(email__iexact=email).first()
        # One message for every failure: no account probing.
        if (
            user is None
            or not user.is_active
            or not user.check_password(serializer.validated_data['password'])
        ):
            return Response(
                {'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(issue_tokens(user))


class RefreshView(PublicAuthView):
    """Trade a valid refresh token for a new pair (the old one is replaced)."""

    serializer_class = RefreshSerializer

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = rotate_refresh(serializer.validated_data['refresh'])
        if tokens is None:
            return Response(
                {'detail': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(tokens)


class ForgotPasswordView(PublicAuthView):
    """Always 200: never reveals whether the email has an account."""

    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()
        lang = serializer.validated_data['lang']
        user = ThirdSideUser.objects.filter(email__iexact=email, is_active=True).first()
        if user and settings.THIRD_SIDE_SEND_EMAIL:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            segment = quote(RESET_SEGMENTS[lang])
            link = (
                f'{settings.THIRD_SIDE_FE_URL}/{lang}/{segment}?uid={uid}&token={token}'
            )
            try:
                send_email(
                    to_email=user.email,
                    subject='Reset your password',
                    body=f'<p><a href="{link}">Reset your password</a></p>',
                )
            except Exception:  # noqa: BLE001 - mail failure must not leak existence
                logger.exception('Password reset email failed')
        return Response({'ok': True})


class ResetPasswordView(PublicAuthView):
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = ThirdSideUser.objects.get(
                pk=force_str(urlsafe_base64_decode(data['uid']))
            )
        except (ThirdSideUser.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, data['token']):
            return Response(
                {'detail': 'Invalid or expired link'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(data['password'], user)
        except DjangoValidationError as error:
            return Response(
                {'password': list(error.messages)}, status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(data['password'])
        user.save(update_fields=['password'])
        return Response(issue_tokens(user))
