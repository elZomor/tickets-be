from rest_framework.permissions import BasePermission

from hita.models import HITAMember


class IsHITAMemberPermission(BasePermission):
    def has_permission(self, request, view):
        hita_member = HITAMember.objects.filter(user=request.user).last()
        return hita_member is not None