from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from hita.models import Achievement, Member
from hita.permissions import IsHITAMemberPermission
from hita.serializers import AchievementCreateSerializer, AchievementViewSerializer
from utils.Response import get_successful_creation_response, get_successful_response
from utils.code_utils import authorize_performer_data


class AchievementViewSet(viewsets.ModelViewSet):
    queryset = Achievement.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = AchievementCreateSerializer

    def create(self, request, *args, **kwargs):
        hita_member = Member.objects.filter(user=self.request.user).last()
        achievement_data = request.data
        achievement_data['performer'] = hita_member.performer.id
        serializer = self.get_serializer(data=achievement_data)
        if not serializer.is_valid():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'status': 'FAILED', 'message': 'Data not create successfully!'},
            )
        instance = serializer.save()
        return get_successful_creation_response(
            data={'id': instance.id}, message='Achievement created successfully!'
        )

    def list(self, request, *args, **kwargs):
        hita_member = Member.objects.filter(user=self.request.user).last()
        achievements = hita_member.performer.achievements.all().order_by('-year')
        serializer = AchievementViewSerializer(achievements, many=True)
        return get_successful_response(data=serializer.data)

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return get_successful_response(message='Achievement updated successfully!')

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
