import requests
from django.contrib.auth.models import User, AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
import jwt


class GoogleJWTAuthentication:

    @staticmethod
    def authenticate(request):
        auth_header = request.headers.get('Authorization')
        if (
            not auth_header
            or not auth_header.startswith('Bearer ')
            or auth_header.startswith('Bearer null')
        ):
            raise AuthenticationFailed('No token supplied')
        try:
            decoded_token = jwt.decode(
                auth_header.split(' ')[1], options={"verify_signature": False}
            )
            user = User.objects.filter(email=decoded_token['email']).first()
            return user, decoded_token
        except jwt.DecodeError:
            token_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            response = requests.get(token_url, headers={'Authorization': auth_header})
            token_info = response.json()
            user = User.objects.filter(email=token_info['email']).first()
            return user, token_info
        except Exception as e:
            print('Auth Error', flush=True)
            print(str(e), flush=True)
            return AnonymousUser(), 'NoData'

    def get_extra_actions(self):
        return []


class FacebookJWTAuthentication:
    @staticmethod
    def authenticate(request):
        auth_header = request.headers.get('Authorization')
        if (
            not auth_header
            or not auth_header.startswith('Bearer ')
            or auth_header.startswith('Bearer null')
        ):
            raise AuthenticationFailed('No token supplied')
        try:
            token_url = "https://graph.facebook.com/v21.0/me?fields=id,first_name,last_name,email"
            response = requests.get(token_url, headers={'Authorization': auth_header})
            token_info = response.json()
            user = User.objects.filter(email=token_info['email']).first()
            return user, token_info
        except Exception as e:
            print('Auth Error', flush=True)
            print(str(e), flush=True)
            raise AuthenticationFailed('Invalid token')

    def get_extra_actions(self):
        return []
