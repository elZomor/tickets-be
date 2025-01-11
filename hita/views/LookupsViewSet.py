from rest_framework import viewsets

from hita.models import (
    StudyType,
    TheaterRole,
    Location,
    ContactTypes,
    TheaterDepartment,
    Faculty,
    CinemaDepartment,
)
from utils.Response import get_successful_response


class ContactTypeViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in ContactTypes]
        return get_successful_response(data=queryset)


class FacultyViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Faculty.choices]
        return get_successful_response(data=queryset)


class DepartmentViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        faculty = request.query_params.get('faculty')
        if faculty == Faculty.CINEMA.value:
            queryset = [label for label, _ in CinemaDepartment.choices]
        else:
            queryset = [label for label, _ in TheaterDepartment.choices]
        return get_successful_response(data=queryset)


class HITALocationViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in Location.choices]
        return get_successful_response(data=queryset)


class SkillsViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        data = list(TheaterRole.objects.values_list('name', flat=True))
        return get_successful_response(data=data)


class StudyTypeViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        queryset = [label for label, _ in StudyType.choices]
        return get_successful_response(data=queryset)
