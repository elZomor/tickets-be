from rest_framework.permissions import BasePermission

from third_side.models import Role


def is_editor(user):
    """True for a signed-in Third Side editor (anonymous users have no role)."""
    return getattr(user, 'role', None) == Role.EDITOR


class IsEditor(BasePermission):
    def has_permission(self, request, view):
        return is_editor(request.user)
