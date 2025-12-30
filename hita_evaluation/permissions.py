from rest_framework.permissions import BasePermission


class CanViewDashboardPermission(BasePermission):
    """Permission class for dashboard access - requires specific permission."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Permission-based access only
        return request.user.has_perm('hita_evaluation.can_view_dashboard')
