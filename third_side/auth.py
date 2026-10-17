"""Third Side's own JWT realm.

Tokens are signed with the project key like every other simplejwt token, but
carry a `ts_user_id` claim and `realm: third_side` instead of `user_id`. The
project-wide JWTAuthentication therefore rejects them, and
ThirdSideJWTAuthentication rejects tokens of the shared django `User`: the
two account systems cannot be mistaken for each other.
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from third_side.models import ThirdSideUser

REALM = 'third_side'
USER_CLAIM = 'ts_user_id'


class ThirdSideRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = cls()
        token[USER_CLAIM] = user.pk
        token['realm'] = REALM
        return token


def issue_tokens(user):
    refresh = ThirdSideRefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


def rotate_refresh(refresh_string):
    """A fresh pair for a valid Third Side refresh token, else None."""
    try:
        token = ThirdSideRefreshToken(refresh_string)
    except TokenError:
        return None
    if token.get('realm') != REALM or USER_CLAIM not in token:
        return None
    user = ThirdSideUser.objects.filter(pk=token[USER_CLAIM], is_active=True).first()
    return issue_tokens(user) if user else None


class ThirdSideJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        if validated_token.get('realm') != REALM or USER_CLAIM not in validated_token:
            raise InvalidToken('Token is not a Third Side token')
        user = ThirdSideUser.objects.filter(pk=validated_token[USER_CLAIM]).first()
        if user is None or not user.is_active:
            raise AuthenticationFailed(
                'User not found or inactive', code='user_inactive'
            )
        return user
