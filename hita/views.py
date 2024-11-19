from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from hita.Exceptions import ResourceNotFound
from hita.models import Performer, HITAMember, Department, StudyType, Location
from hita.permissions import IsHITAMemberPermission
from hita.serializers import (
    PerformerViewSerializer,
    HITAMemberViewSerializer,
    HITAMemberCreateSerializer,
)


class PerformerViewSet(viewsets.ModelViewSet):
    model = Performer
    queryset = Performer.objects.all().order_by(
        'hita_member__first_name', 'hita_member__last_name'
    )
    permission_classes = [IsHITAMemberPermission]
    serializer_class = PerformerViewSerializer

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {'hita_member__user__username': self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        if not obj:
            raise ResourceNotFound(f'Performer profile with username: {self.kwargs[lookup_url_kwarg]} does not exist')
        self.check_object_permissions(self.request, obj)
        return obj

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
            return Response(
                data={'status': 'FAILED', 'message': 'Performer profile already exist'},
                status=status.HTTP_409_CONFLICT,
            )
        Performer.objects.create(hita_user=hita_member)
        return Response(
            data={'status': 'SUCCESS', 'message': 'Created Successfully!'},
            status=status.HTTP_201_CREATED,
        )


class DepartmentViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Department.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class StudyTypeViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in StudyType.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class HITALocationViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Location.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class HitaMemberViewSet(viewsets.ModelViewSet):
    model = HITAMember
    queryset = HITAMember.objects.all().order_by('first_name', 'last_name')
    serializer_class = HITAMemberViewSerializer
    permission_classes = [IsHITAMemberPermission]

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsHITAMemberPermission()]

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {'user__username': self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        if not obj:
            raise ResourceNotFound(f'HITAMember profile with username: {self.kwargs[lookup_url_kwarg]} does not exist')
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
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

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'status': 'FAILED', 'message': 'You are not allowed to delete.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
