from http import HTTPStatus

from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config.pagination import CustomPagination
from hita import permissions
from hita.models import Performer, HITAMember
from hita.permissions import IsHITAMemberPermission
from hita.serializers import PerformerViewSerializer


class PerformerViewSet(viewsets.ModelViewSet):
    model = Performer
    queryset = Performer.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = PerformerViewSerializer

    def get_serializer_context(self):
        context = super(PerformerViewSet, self).get_serializer_context()
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        context.update({'hita_member': hita_member})
        return context

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=request.user).last()
        if Performer.objects.filter(hita_user=hita_member).exists():
            return Response(data={'status': 'FAILED', 'message': 'Performer profile already exist'},
                            status=status.HTTP_409_CONFLICT)
        Performer.objects.create(hita_user=hita_member)
        return Response(data={'status': 'SUCCESS', 'message': 'Created Successfully!'}, status=status.HTTP_201_CREATED)
