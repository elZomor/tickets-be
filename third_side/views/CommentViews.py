from rest_framework import mixins
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from third_side.models import Comment, Role
from third_side.serializers import CommentSerializer


class CommentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = CommentSerializer

    def get_queryset(self):
        queryset = Comment.objects.select_related('user', 'article').order_by(
            '-created_at', '-id'
        )
        profile = getattr(self.request.user, 'third_side_profile', None)
        if profile and profile.role == Role.EDITOR:
            return queryset
        return queryset.filter(is_hidden=False)

    def get_permissions(self):
        if getattr(self.request, 'method', None) == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _is_owner_or_editor(self, instance):
        if instance.user_id == self.request.user.id:
            return True
        profile = getattr(self.request.user, 'third_side_profile', None)
        return bool(profile and profile.role == Role.EDITOR)

    def perform_update(self, serializer):
        if not self._is_owner_or_editor(serializer.instance):
            self.permission_denied(self.request)
        serializer.save()

    def perform_destroy(self, instance):
        if not self._is_owner_or_editor(instance):
            self.permission_denied(self.request)
        instance.delete()
