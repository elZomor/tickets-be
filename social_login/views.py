import jwt
from django.contrib.auth.models import User
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
import uuid

from social_login.authentication import (
    FacebookJWTAuthentication,
    GoogleJWTAuthentication,
)
from social_login.models import Policy
from utils.Response import get_bad_request_response, get_successful_creation_response


class GoogleLogin(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []

    @action(detail=False, methods=['GET'], url_path='login/callback')
    def callback(self, request, *args, **kwargs):
        try:
            user, account_info = GoogleJWTAuthentication.authenticate(request)
            if not user:
                user_object = {
                    'username': uuid.uuid4().hex[:30],
                    'email': account_info.get('email'),
                    'is_active': True,
                }
                if account_info.get('given_name') is not None:
                    user_object['first_name'] = account_info.get('given_name')
                if account_info.get('family_name') is not None:
                    user_object['last_name'] = account_info.get('family_name')
                user = User.objects.create_user(**user_object)
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "status": "SUCCESS",
                    "data": {
                        'ACCESS_TOKEN': str(refresh.access_token),
                        'REFRESH_TOKEN': str(refresh),
                    },
                }
            )
        except Exception as e:
            print('!' * 20, flush=True)
            print(str(e), flush=True)
            print('!' * 20, flush=True)
            return Response(
                {
                    "message": "Login failed",
                    "tokens": 'token_info',
                }
            )


class FacebookLogin(viewsets.GenericViewSet):
    @action(detail=False, methods=['POST'], url_path='revoke')
    def remove_facebook_data(self, request, *args, **kwargs):
        try:
            data = request.data
            email = data.get('email')

            if not email:
                return Response(
                    {'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST
                )

            # Find the user by email
            user = User.objects.filter(email=email).first()

            if not user:
                return Response(
                    {'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND
                )

            # Delete the user
            user.delete()

            return Response(
                {'message': 'User data deleted successfully'}, status=status.HTTP_200_OK
            )
        except Exception as e:
            print('Facebook Login Exception', flush=True)
            print(e, flush=True)
            return Response(
                {'error': 'Invalid JSON format'}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['GET'], url_path='callback')
    def callback(self, request, *args, **kwargs):
        try:
            user, account_info = FacebookJWTAuthentication.authenticate(request)
            if not user:
                user_object = {
                    'username': uuid.uuid4().hex[:30],
                    'email': account_info.get('email'),
                    'is_active': True,
                }
                if account_info.get('given_name') is not None:
                    user_object['first_name'] = account_info.get('given_name')
                if account_info.get('family_name') is not None:
                    user_object['last_name'] = account_info.get('family_name')
                user = User.objects.create_user(**user_object)
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "status": "SUCCESS",
                    "data": {
                        'ACCESS_TOKEN': str(refresh.access_token),
                        'REFRESH_TOKEN': str(refresh),
                    },
                }
            )
        except Exception as e:
            print('!' * 20, flush=True)
            print(str(e), flush=True)
            print('!' * 20, flush=True)
            return Response(
                {
                    "message": "Login failed",
                    "tokens": 'token_info',
                }
            )


class EmailSignup(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []

    @action(detail=False, methods=['POST'], url_path='signup')
    def signup(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        # Validate email
        if not email:
            return get_bad_request_response(data={'email': 'Email is required'})

        # Check existing user
        if User.objects.filter(email=email).exists():
            return get_bad_request_response(
                data={'email': 'An account with this email already exists'}
            )

        # Validate password
        if not password:
            return get_bad_request_response(data={'password': 'Password is required'})

        if len(password) < 8:
            return get_bad_request_response(
                data={'password': 'Password must be at least 8 characters'}
            )

        # Create user (active like Google OAuth)
        user = User.objects.create_user(
            username=uuid.uuid4().hex[:30],
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
        )
        user.set_password(password)
        user.save()

        # Generate tokens with same format as Google OAuth
        refresh = RefreshToken.for_user(user)
        return get_successful_creation_response(
            data={
                'ACCESS_TOKEN': str(refresh.access_token),
                'REFRESH_TOKEN': str(refresh),
            }
        )

    @action(detail=False, methods=['POST'], url_path='login')
    def login(self, request, *args, **kwargs):
        # Accept either 'email' or 'username' field as identifier
        identifier = request.data.get('email', '') or request.data.get('username', '')
        identifier = identifier.strip().lower() if identifier else ''
        password = request.data.get('password', '')

        if not identifier or not password:
            return get_bad_request_response(
                data={'detail': 'Email/username and password are required'}
            )

        # Find user by email first, then by username
        user = User.objects.filter(email=identifier).first()
        if not user:
            user = User.objects.filter(username__iexact=identifier).first()

        if not user or not user.check_password(password):
            return get_bad_request_response(
                data={'detail': 'Invalid credentials'}
            )

        if not user.is_active:
            return get_bad_request_response(
                data={'detail': 'Account is not active'}
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'status': 'SUCCESS',
                'data': {
                    'ACCESS_TOKEN': str(refresh.access_token),
                    'REFRESH_TOKEN': str(refresh),
                },
            }
        )


class PolicyViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []

    @action(detail=False, methods=['GET'], url_path='privacy-policy')
    def privacy_policy(self, request, *args, **kwargs):
        policy = Policy.objects.filter(type='PRIVACY', is_active=True).last()
        return Response(
            data={'content': policy.content, 'last_updated': policy.updated_at},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['GET'], url_path='terms-and-conditions')
    def terms_and_conditions(self, request, *args, **kwargs):
        policy = Policy.objects.filter(type='TAC', is_active=True).last()
        return Response(
            data={'content': policy.content, 'last_updated': policy.updated_at},
            status=status.HTTP_200_OK,
        )
