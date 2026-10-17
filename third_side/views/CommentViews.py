from django.db.models import Count
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import Comment, CommentLike
from third_side.permissions import is_editor
from third_side.serializers import CommentSerializer


class CommentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """Comments. List filter: ?article=<id>. Newest first."""

    serializer_class = CommentSerializer
    authentication_classes = [ThirdSideJWTAuthentication]
    throttle_scope = 'third_side_write'

    def get_queryset(self):
        queryset = (
            Comment.objects.select_related('user', 'article')
            .annotate(likes_total=Count('likes'))
            .order_by('-created_at', '-id')
        )
        if not (is_editor(self.request.user)):
            queryset = queryset.filter(is_hidden=False)
        if self.action == 'list' and self.request.query_params.get('article'):
            queryset = queryset.filter(article_id=self.request.query_params['article'])
        return queryset

    def get_permissions(self):
        if getattr(self.request, 'method', None) == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _is_owner_or_editor(self, instance):
        if instance.user_id == self.request.user.id:
            return True
        return bool(is_editor(self.request.user))

    def perform_update(self, serializer):
        if not self._is_owner_or_editor(serializer.instance):
            self.permission_denied(self.request)
        serializer.save()

    def perform_destroy(self, instance):
        if not self._is_owner_or_editor(instance):
            self.permission_denied(self.request)
        instance.delete()

    def _respond(self, comment_id, http_status=status.HTTP_200_OK):
        comment = self.get_queryset().get(pk=comment_id)
        return Response(self.get_serializer(comment).data, status=http_status)

    @action(detail=True, methods=['post', 'delete'], url_path='like')
    def like(self, request, pk=None):
        """POST likes, DELETE unlikes. Both idempotent; returns the comment."""
        comment = self.get_object()
        if request.method == 'POST':
            CommentLike.objects.get_or_create(user=request.user, comment=comment)
        else:
            CommentLike.objects.filter(user=request.user, comment=comment).delete()
        return self._respond(comment.pk)
