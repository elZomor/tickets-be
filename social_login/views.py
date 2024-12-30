from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
import uuid
from rest_framework_simplejwt.tokens import RefreshToken

from social_login.authentication import (
    GoogleJWTAuthentication,
    FacebookJWTAuthentication,
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
                user = User.objects.create_user(
                    **{
                        'username': uuid.uuid4().hex[:30],
                        'first_name': account_info.get('given_name'),
                        'last_name': account_info.get('family_name'),
                        'email': account_info.get('email'),
                        'is_active': True,
                    }
                )
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
                user = User.objects.create_user(
                    **{
                        'username': uuid.uuid4().hex[:30],
                        'first_name': account_info.get('given_name'),
                        'last_name': account_info.get('family_name'),
                        'email': account_info.get('email'),
                        'is_active': True,
                    }
                )
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
    @action(detail=False, methods=['POST'], url_path='signup')
    def signup(self, request, *args, **kwargs):
        if User.objects.filter(email=request.data['email']).exists():
            return get_bad_request_response(data='Email already registered')
        user = User.objects.create_user(
            **{
                'username': uuid.uuid4().hex[:30],
                'email': request.data['email'],
                'is_active': False,
            }
        )
        user.set_password(request.data['password'])
        user.save()
        refresh = RefreshToken.for_user(user)
        return get_successful_creation_response(data={
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


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
