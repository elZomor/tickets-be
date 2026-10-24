"""Authorization, Django style: Groups carry model permissions.

A reader is a Third Side user with no group. Staff are given Groups (roles,
defined in services/roles.py); a view asks for the permission it needs, never
for a role name.
"""

from rest_framework.permissions import BasePermission

from third_side.models import ThirdSideUser

APP = 'third_side'


def has_perm(user, codename):
    """True when a signed-in Third Side user holds `third_side.<codename>`.

    Anonymous users and tokens of the shared django User never do.
    """
    return isinstance(user, ThirdSideUser) and user.has_perm(f'{APP}.{codename}')


def model_perms(model):
    """The usual per-action permissions of a viewset over one model."""
    return {
        'list': f'view_{model}',
        'retrieve': f'view_{model}',
        'doc': f'view_{model}',
        'create': f'add_{model}',
        'update': f'change_{model}',
        'partial_update': f'change_{model}',
        'destroy': f'delete_{model}',
    }


class RequirePerm(BasePermission):
    """Looks the permission up in the view's `required_perms`.

    The key is the viewset action, else the lowercase HTTP method; '*' is the
    fallback. A key with no entry is refused.
    """

    def has_permission(self, request, view):
        perms = view.required_perms
        key = getattr(view, 'action', None) or request.method.lower()
        codename = perms.get(key, perms.get('*'))
        return codename is not None and has_perm(request.user, codename)


class EmailVerified(BasePermission):
    """Signed-in readers must have confirmed their email (staff are exempt).

    The 403 carries `code: email_not_verified` so the FE can offer a resend.
    """

    message = {
        'detail': 'Confirm your email address first',
        'code': 'email_not_verified',
    }

    def has_permission(self, request, view):
        user = request.user
        return isinstance(user, ThirdSideUser) and user.can_contribute
