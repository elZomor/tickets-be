from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from hita.models import Achievement, HITAMember
from hita.permissions import IsHITAMemberPermission
from hita.serializers import AchievementCreateSerializer, AchievementViewSerializer
from utils.code_utils import authorize_performer_data


class AchievementViewSet(viewsets.ModelViewSet):
    queryset = Achievement.objects.all()
    permission_classes = [IsHITAMemberPermission]
    serializer_class = AchievementCreateSerializer

    def create(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        achievement_data = request.data
        achievement_data['performer'] = hita_member.performer.id
        serializer = self.get_serializer(data=achievement_data)
        if not serializer.is_valid():
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'status': 'FAILED', 'message': 'Data not create successfully!'},
            )
        instance = serializer.save()
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                'status': 'SUCCESS',
                'message': 'Achievement created successfully!',
                'data': {'id': instance.id},
            },
        )

    def list(self, request, *args, **kwargs):
        hita_member = HITAMember.objects.filter(user=self.request.user).last()
        achievements = hita_member.performer.achievements.all().order_by('-year')
        serializer = AchievementViewSerializer(achievements, many=True)
        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': 'SUCCESS',
                'message': 'Achievement created successfully!',
                'data': serializer.data,
            },
        )

    @authorize_performer_data
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            status=status.HTTP_200_OK,
            data={'status': 'SUCCESS', 'message': 'Achievement updated successfully!'},
        )

    @authorize_performer_data
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
