from rest_framework import status
from rest_framework import viewsets

from hita.models import Department, StudyType, ContactType, TheaterRole, Location
from rest_framework.response import Response


class ContactTypeViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in ContactType.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class DepartmentViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Department.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class HITALocationViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Location.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )


class SkillsViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        data = list(TheaterRole.objects.values_list('name', flat=True))
        return Response(
            data={'status': 'SUCCESS', 'data': data}, status=status.HTTP_200_OK
        )


class StudyTypeViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in StudyType.choices]
        return Response(
            data={'status': 'SUCCESS', 'data': queryset}, status=status.HTTP_200_OK
        )
