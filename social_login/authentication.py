import requests
from django.contrib.auth.models import User
from rest_framework.exceptions import AuthenticationFailed


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
            token_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            response = requests.get(token_url, headers={'Authorization': auth_header})
            token_info = response.json()
            user = User.objects.filter(email=token_info['email']).first()
            return user, token_info
        except Exception as e:
            print('Auth Error', flush=True)
            print(str(e), flush=True)
            raise AuthenticationFailed('Invalid token')

    def get_extra_actions(self):
        # If you don't need extra actions, just return an empty list
        return []
