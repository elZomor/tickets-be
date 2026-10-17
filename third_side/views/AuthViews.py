import logging
import uuid
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from config.constants import SEND_EMAIL
from third_side.models import Profile
from utils.email_utils import send_email

# The FE serves the reset page at a localized URL segment (accountPaths.ts).
RESET_SEGMENTS = {'ar': 'كلمة-مرور-جديدة', 'en': 'reset-password', 'ro': 'parola-noua'}

User = get_user_model()
logger = logging.getLogger(__name__)


class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
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


def _token_pair(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


class SignupView(APIView):
    """Create a reader account and return a simplejwt pair, like /token/."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = SignupSerializer

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.create_user(
            username=uuid.uuid4().hex[:30],
            email=data['email'],
            password=data['password'],
            first_name=data['name'].strip(),
            is_active=True,
        )
        Profile.objects.get_or_create(user=user)
        return Response(_token_pair(user), status=status.HTTP_201_CREATED)


class ForgotPasswordView(APIView):
    """Always 200: never reveals whether the email has an account."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()
        lang = serializer.validated_data['lang']
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user and SEND_EMAIL:
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


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data['uid'])))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
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
        return Response(_token_pair(user))
