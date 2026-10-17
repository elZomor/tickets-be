from django.db.models import Avg, Case, Count, F, IntegerField, Q, Value, When
from django.http import Http404
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.models import Article, Role
from third_side.models.Article import ArticleStatus
from third_side.permissions import IsEditor
from third_side.read_serializers import (
    ArticleDetailSerializer,
    ArticleReadSerializer,
)
from third_side.serializers import ArticleSerializer


class ArticleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """Public reads are localized with ?lang=ar|en|ro.

    List filters: ?category=<slug> ?group=<slug> ?tag=<slug> ?critic=<id>
    ?featured=true ?search=<text>. Editors write with the plain serializer.
    """

    def get_serializer_class(self):
        if getattr(self.request, 'method', None) != 'GET':
            return ArticleSerializer
        if self.action in ('retrieve', 'by_slug'):
            return ArticleDetailSerializer
        return ArticleReadSerializer

    def _is_editor(self):
        profile = getattr(self.request.user, 'third_side_profile', None)
        return bool(profile and profile.role == Role.EDITOR)

    def get_queryset(self):
        queryset = (
            Article.objects.select_related('category', 'critic')
            .prefetch_related('translations', 'tags')
            .annotate(rating_avg=Avg('ratings__value'), rating_count=Count('ratings'))
            .order_by('-published_at', '-id')
        )
        if not self._is_editor():
            queryset = queryset.filter(is_hidden=False, status=ArticleStatus.PUBLISHED)
        if self.action != 'list':
            return queryset
        params = self.request.query_params
        if params.get('category'):
            queryset = queryset.filter(category__slug=params['category'])
        if params.get('group'):
            queryset = queryset.filter(category__group__slug=params['group'])
        if params.get('tag'):
            queryset = queryset.filter(tags__slug=params['tag'])
        if params.get('critic'):
            queryset = queryset.filter(critic_id=params['critic'])
        if params.get('featured') in ('1', 'true'):
            queryset = queryset.filter(is_featured=True)
        if params.get('search'):
            term = params['search']
            queryset = queryset.filter(
                Q(title__icontains=term) | Q(translations__title__icontains=term)
            ).distinct()
        return queryset

    def get_permissions(self):
        if getattr(self.request, 'method', None) == 'GET' or self.action in ('read',):
            return [AllowAny()]
        return [IsAuthenticated(), IsEditor()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-slug/(?P<slug>[^/]+)')
    def by_slug(self, request, slug=None):
        """Detail by slug in ANY locale (the slug identifies the translation)."""
        article = (
            self.get_queryset()
            .filter(Q(translations__slug=slug) | Q(slug=slug))
            .distinct()
            .first()
        )
        if article is None:
            raise Http404
        return Response(self.get_serializer(article).data)

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Other articles, same category first, newest first (paginated)."""
        article = self.get_object()
        queryset = (
            self.get_queryset()
            .exclude(pk=article.pk)
            .annotate(
                other_category=Case(
                    When(category_id=article.category_id, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by('other_category', '-published_at', '-id')
        )
        page = self.paginate_queryset(queryset)
        serializer = ArticleReadSerializer(
            page, many=True, context=self.get_serializer_context()
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'], authentication_classes=[])
    def read(self, request, pk=None):
        """Count a read. Public and idempotent per request, not per reader."""
        article = self.get_object()
        Article.objects.filter(pk=article.pk).update(read_count=F('read_count') + 1)
        return Response({'read_count': article.read_count + 1})
