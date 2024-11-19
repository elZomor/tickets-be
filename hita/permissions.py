from rest_framework.permissions import BasePermission

from hita.models import HITAMember, Status


class IsHITAMemberPermission(BasePermission):
    def has_permission(self, request, view):
        hita_member = HITAMember.objects.filter(user=request.user, request_status=Status.APPROVED.value).last()
        return hita_member is not None
