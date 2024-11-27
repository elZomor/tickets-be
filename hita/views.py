from rest_framework import status
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from hita.Exceptions import ResourceNotFound
from hita.models import Performer, HITAMember, Department, StudyType, Location, TheaterRole
from hita.permissions import IsHITAMemberPermission
from hita.serializers import (
    HITAMemberViewSerializer,
    HITAMemberCreateSerializer,
    PerformerViewAllSerializer,
    PerformerViewOneSerializer, PerformerCreateSerializer, TheaterRoleViewSerializer,
)


class PerformerViewSet(viewsets.ModelViewSet):
    model = Performer
    queryset = Performer.objects.all().order_by(
        'hita_member__first_name', 'hita_member__last_name'
    )
    permission_classes = [IsHITAMemberPermission]
    serializer_class = PerformerViewOneSerializer

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {'hita_member__user__username': self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        if not obj:
            raise ResourceNotFound(
                f'Performer profile with username: {self.kwargs[lookup_url_kwarg]} does not exist'
            )
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_context(self):
        context = super(PerformerViewSet, self).get_serializer_context()
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        context.update({'hita_member': hita_member})
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            data={'status': 'SUCCESS', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            serializer = PerformerViewAllSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=request.user).last()
        if Performer.objects.filter(hita_member=hita_member).exists():
            return Response(
                data={'status': 'FAILED', 'message': 'Performer profile already exist'},
                status=status.HTTP_409_CONFLICT,
            )
        performer_data = request.data.get('performer_data')
        performer_data['hita_member'] = hita_member.id
        serializer = PerformerCreateSerializer(data=performer_data)
        if not serializer.is_valid():
            return Response(
                {'status': 'FAILED', 'data': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        performer = serializer.save()
        skills = TheaterRole.objects.filter(name__in=performer_data.get('skills_tags'))
        performer.skills_tags.add(*skills)
        print('performer', flush=True)
        print(performer, flush=True)
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


class SkillsViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        data = list(TheaterRole.objects.values_list('name', flat=True))
        return Response(
            data={'status': 'SUCCESS', 'data': data}, status=status.HTTP_200_OK
        )


class HITALocationViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Location.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


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
            print(serializer.errors, flush=True)
            print(serializer.error_messages, flush=True)
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
            data={'status': 'SUCCESS', 'data': {'status': hita_member.request_status}},
            status=status.HTTP_200_OK,
        )
