from authlib.jose import jwt
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


def get_public_key():
    with open('/app/clerk/public_key.pem', 'r') as file:
        return file.read()


class ClerkJWTAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer ') or auth_header.startswith('Bearer null'):
            raise AuthenticationFailed('No token supplied')

        token = auth_header.split(' ')[1]
        try:
            decoded = jwt.decode(token, get_public_key())
            user = User.objects.get(email=decoded.get('email'))
            return user, token
        except Exception as e:
            print(type(e), flush=True)
            raise AuthenticationFailed(str(e))
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')
        except Exception as e:
            print(str(e), flush=True)
            raise AuthenticationFailed('Invalid token')
