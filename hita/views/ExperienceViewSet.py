from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from hita.models import Experience, HITAMember, TheaterRole
from hita.permissions import IsHITAMemberPermission
from hita.serializers import ExperienceCreateSerializer, ExperienceViewSerializer
from utils.Response import get_bad_request_response, get_successful_creation_response, get_successful_response
from utils.code_utils import authorize_performer_data


class ExperienceViewSet(viewsets.ModelViewSet):
    queryset = Experience.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = ExperienceCreateSerializer

    def create(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        experience_data = request.data
        experience_data['performer'] = hita_member.performer.id
        serializer = ExperienceCreateSerializer(data=experience_data)
        if not serializer.is_valid():
            return get_bad_request_response(message='Data not create successfully!', data=serializer.errors)

        instance = serializer.save()
        if roles := experience_data.get('roles'):
            roles = TheaterRole.objects.filter(name__in=roles)
            instance.role.set(roles)
        return get_successful_creation_response(data={'id': instance.id}, message='Experience created successfully!')


    def list(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        experiences = hita_member.performer.experiences.all().order_by('-year')
        serializer = ExperienceViewSerializer(experiences, many=True)
        return get_successful_response(data=serializer.data)


    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        instance = self.get_object()
        if roles := request.data.get('roles'):
            roles = TheaterRole.objects.filter(name__in=roles)
            instance.role.set(roles)
        return get_successful_response(message='Experience updated successfully!')

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
