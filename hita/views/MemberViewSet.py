from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, mixins
from rest_framework import status

from hita.Exceptions import ResourceNotFound
from hita.models import HITAMember
from hita.permissions import IsHITAMemberPermission
from hita.serializers import HITAMemberViewSerializer, HITAMemberCreateSerializer
from rest_framework.decorators import action


class HitaMemberViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    model = HITAMember
    queryset = HITAMember.objects.all().order_by('first_name', 'last_name')
    serializer_class = HITAMemberViewSerializer

    def get_permissions(self):
        if self.action in ['create', 'member_status', 'retrieve_member']:
            return [IsAuthenticated()]
        return [IsHITAMemberPermission()]

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {'user': self.request.user}
        obj = queryset.filter(**filter_kwargs).first()
        if not obj:
            raise ResourceNotFound(
                f'HITAMember profile with username: {self.kwargs[lookup_url_kwarg]} does not exist'
            )
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, methods=['GET'], url_path='me')
    def retrieve_member(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {
                    'status': 'SUCCESS',
                    'data': serializer.data,
                }
            )
        except ResourceNotFound:
            return Response(
                {
                    'status': 'FAILED',
                    'message': 'No Member Found',
                }
            )

    def create(self, request, *args, **kwargs):

        serializer = HITAMemberCreateSerializer(
            data=request.data, context={'request': request}
        )
        if not serializer.is_valid():
            return Response(
                {'status': 'FAILED', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member = serializer.save()
        return Response(
            {'status': 'SUCCESS', 'data': HITAMemberViewSerializer(member).data},
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['GET'], detail=False, url_path='status')
    def member_status(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=request.user).last()
        if not hita_member:
            return Response(
                data={'status': 'SUCCESS', 'data': {'status': 'NOT_REGISTERED'}},
                status=status.HTTP_200_OK,
            )
        return Response(
            data={
                'status': 'SUCCESS',
                'data': {
                    'status': hita_member.request_status,
                    'performer': hita_member.has_performer,
                    'username': hita_member.user.username,
                },
            },
            status=status.HTTP_200_OK,
        )
