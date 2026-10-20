from django.db.models import Avg, Case, Count, F, IntegerField, Q, Value, When
from django.http import Http404
from django.utils import timezone
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.views.audit_mixin import AuditedMixin
from third_side.models import Article
from third_side.models.Article import ArticleStatus, live_q
from third_side.permissions import IsEditor, is_editor
from third_side.read_serializers import (
    ArticleDetailSerializer,
    ArticleReadSerializer,
)
from third_side.serializers import ArticleSerializer
from third_side.services.media_urls import to_url
from third_side.services.translations import translation_map


class ArticleViewSet(
    AuditedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """Public reads are localized with ?lang=ar|en|ro.

    List filters: ?category=<slug> ?group=<slug> ?tag=<slug> ?critic=<id>
    ?featured=true ?search=<text>; editors also get ?editor=<user id>. Editors write with the plain serializer.
    """

    authentication_classes = [ThirdSideJWTAuthentication]

    @property
    def throttle_scope(self):
        # Only the public counter is throttled; reads of content are not.
        return 'third_side_read' if self.action == 'read' else None

    def get_serializer_class(self):
        if getattr(self.request, 'method', None) != 'GET':
            return ArticleSerializer
        if self.action in ('retrieve', 'by_slug'):
            return ArticleDetailSerializer
        return ArticleReadSerializer

    def _is_editor(self):
        return bool(is_editor(self.request.user))

    def get_queryset(self):
        if self._is_editor():
            # Show scheduled articles whose time has come as published.
            Article.objects.filter(
                status=ArticleStatus.SCHEDULED, published_at__lte=timezone.now()
            ).update(status=ArticleStatus.PUBLISHED)
        queryset = (
            Article.objects.select_related('category', 'critic', 'editor')
            .prefetch_related('translations', 'tags')
            .annotate(
                rating_avg=Avg('ratings__value'),
                rating_count=Count('ratings', distinct=True),
            )
            .order_by('-published_at', '-id')
        )
        if not self._is_editor():
            queryset = queryset.filter(live_q(), is_hidden=False)
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
        if params.get('editor') and self._is_editor():
            queryset = queryset.filter(editor_id=params['editor'])
        if params.get('featured') in ('1', 'true'):
            queryset = queryset.filter(is_featured=True)
        if params.get('search'):
            term = params['search']
            queryset = queryset.filter(
                Q(title__icontains=term) | Q(translations__title__icontains=term)
            ).distinct()
        return queryset

    def get_permissions(self):
        if self.action == 'doc':
            return [IsAuthenticated(), IsEditor()]
        if getattr(self.request, 'method', None) == 'GET' or self.action in ('read',):
            return [AllowAny()]
        return [IsAuthenticated(), IsEditor()]

    def _refuse_if_published(self, article):
        """A published article is final: no edits, no state change, no delete."""
        if article.status == ArticleStatus.PUBLISHED:
            raise ValidationError(
                {
                    'detail': 'A published article is locked: it cannot be edited, '
                    'changed to another state or deleted.'
                }
            )

    def update(self, request, *args, **kwargs):
        self._refuse_if_published(self.get_object())
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._refuse_if_published(self.get_object())
        return super().destroy(request, *args, **kwargs)

    def save_new(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def doc(self, request, pk=None):
        """Editor-only: every language's text in the shape the admin editor saves."""
        article = self.get_object()
        translations = translation_map(article, request)
        original = article.original_language
        return Response(
            {
                'id': article.pk,
                'title': {k: v['title'] for k, v in translations.items()},
                'slug': {k: v['slug'] for k, v in translations.items()},
                'content': {k: v['content'] for k, v in translations.items()},
                'isOriginalLanguage': {k: k == original for k in translations},
                'aiGenerated': {
                    k: bool(v['is_ai_generated']) and k != original
                    for k, v in translations.items()
                },
                'status': article.status,
                'publishedAt': article.published_at,
                'submittedAt': article.created_at,
                'critic': article.critic_id,
                'editor': article.editor_id,
                'cover': to_url(article.cover_url, request) or None,
                'category': article.category_id,
                'viaWebsite': article.via_website,
                'seoTitle': {k: v['seo_title'] for k, v in translations.items()},
                'metaDescription': {
                    k: v['meta_description'] for k, v in translations.items()
                },
                'noindex': article.noindex,
                'canonicalUrl': article.canonical_url,
                'tags': [tag.slug for tag in article.tags.all()],
            }
        )

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
