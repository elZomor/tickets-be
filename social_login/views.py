from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
import uuid

from rest_framework_simplejwt.tokens import RefreshToken

from config.constants import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from hita import permissions
from social_login.authentication import GoogleJWTAuthentication


class GoogleLogin(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []

    @action(detail=False, methods=['GET'], url_path='login/callback')
    def callback(self, request, *args, **kwargs):
        try:
            user, account_info = GoogleJWTAuthentication.authenticate(request)
            if not user:
                user = User.objects.create_user(**{
                    'username': uuid.uuid4().hex[:30],
                    'first_name': account_info.get('given_name'),
                    'last_name': account_info.get('family_name'),
                    'email': account_info.get('email'),
                    'is_active': True
                })
            refresh = RefreshToken.for_user(user)
            return Response({
                "status": "SUCCESS",
                "data": {
                    'ACCESS_TOKEN': str(refresh.access_token),
                    'REFRESH_TOKEN': str(refresh),
                }
            })
        except Exception as e:
            print('!' * 20, flush=True)
            print(str(e), flush=True)
            print('!' * 20, flush=True)
            return Response({
                "message": "Login failed",
                "tokens": 'token_info',
            })
