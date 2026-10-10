from rest_framework.permissions import BasePermission

from third_side.models import Role


class IsEditor(BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, 'third_side_profile', None)
        return bool(profile and profile.role == Role.EDITOR)
