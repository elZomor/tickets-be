from rest_framework import mixins
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from third_side.models import Article, Role
from third_side.models.Article import ArticleStatus
from third_side.permissions import IsEditor
from third_side.serializers import ArticleSerializer


class ArticleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        queryset = Article.objects.select_related('category', 'critic')
        profile = getattr(self.request.user, 'third_side_profile', None)
        if profile and profile.role == Role.EDITOR:
            return queryset
        return queryset.filter(is_hidden=False, status=ArticleStatus.PUBLISHED)

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsEditor()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
