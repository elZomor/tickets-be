from django.db.models import Count, Q
from django.http import Http404
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.models import Critic
from third_side.models.Article import ArticleStatus
from third_side.permissions import IsEditor
from third_side.read_serializers import CriticReadSerializer
from third_side.serializers import CriticSerializer


class CriticViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """Writers. Public reads are localized with ?lang=; their articles are
    GET /articles?critic=<id>."""

    def get_serializer_class(self):
        if getattr(self.request, 'method', None) == 'GET':
            return CriticReadSerializer
        return CriticSerializer

    def get_queryset(self):
        return (
            Critic.objects.select_related('main_category')
            .annotate(
                article_count=Count(
                    'articles',
                    filter=Q(
                        articles__is_hidden=False,
                        articles__status=ArticleStatus.PUBLISHED,
                    ),
                )
            )
            .order_by('name', 'id')
        )

    def filter_queryset(self, queryset):
        # Reader accounts that submitted but have nothing published are not
        # public writers yet.
        if self.action in ('list', 'by_slug'):
            queryset = queryset.filter(Q(user__isnull=True) | Q(article_count__gt=0))
        return super().filter_queryset(queryset)

    def get_authenticators(self):
        if getattr(self.request, 'method', None) == 'GET':
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if getattr(self.request, 'method', None) == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsEditor()]

    @action(detail=False, methods=['get'], url_path=r'by-slug/(?P<slug>[^/]+)')
    def by_slug(self, request, slug=None):
        """A writer by their URL segment in ANY locale."""
        for critic in self.get_queryset():
            if slug in critic.slug_i18n.values():
                return Response(self.get_serializer(critic).data)
        raise Http404
