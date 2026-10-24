from django.db.models import Avg, Case, Count, F, IntegerField, Q, Value, When
from django.http import Http404
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.views.audit_mixin import AuditedMixin
from third_side.models import Article
from third_side.models.Article import (
    AUTHOR_EDITABLE,
    AUTHOR_SETS,
    PUBLISH_STATUSES,
    ArticleStatus,
    live_q,
)
from third_side.permissions import has_perm
from third_side.read_serializers import (
    ArticleDetailSerializer,
    ArticleReadSerializer,
)
from third_side.serializers import ArticleSerializer
from third_side.services.media_urls import to_url
from third_side.services.publishing import promote_due_articles
from third_side.services.translations import translation_map


# Fields only staff who manage articles (change_article) may set; an author
# working on their own piece may not.
STAFF_ONLY_FIELDS = {'editor': None, 'is_hidden': False, 'published_at': None}


class ArticlePermission(BasePermission):
    """Who may write articles.

    add_article: create. change_article: edit any article. An author (add_article
    without change_article) edits only their own piece, and only while it is in
    AUTHOR_EDITABLE. Reading one article's editor doc needs view_article, or being
    its author. Deleting needs delete_article.
    """

    def has_permission(self, request, view):
        user = request.user
        if view.action == 'create':
            return has_perm(user, 'add_article')
        if view.action in ('update', 'partial_update'):
            return has_perm(user, 'change_article') or has_perm(user, 'add_article')
        if view.action == 'destroy':
            return has_perm(user, 'delete_article')
        if view.action == 'doc':
            return has_perm(user, 'view_article') or has_perm(user, 'add_article')
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if view.action == 'doc':
            return has_perm(user, 'view_article') or obj.created_by_id == user.pk
        if view.action in ('update', 'partial_update'):
            if has_perm(user, 'change_article'):
                return True
            return obj.created_by_id == user.pk and obj.status in AUTHOR_EDITABLE
        return True


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

    def _scope(self):
        """What the caller reads: 'all' (staff who view articles), 'own' (authors:
        the live ones plus their own pieces), else 'live' (readers, anonymous)."""
        user = self.request.user
        if has_perm(user, 'view_article'):
            return 'all'
        if has_perm(user, 'add_article'):
            return 'own'
        return 'live'

    def get_queryset(self):
        scope = self._scope()
        if scope != 'live':
            # Show scheduled articles whose time has come as published.
            promote_due_articles()
        queryset = (
            Article.objects.select_related('category', 'critic', 'editor')
            .prefetch_related('translations', 'tags')
            .annotate(
                rating_avg=Avg('ratings__value'),
                rating_count=Count('ratings', distinct=True),
            )
            .order_by('-published_at', '-id')
        )
        if scope == 'own':
            queryset = queryset.filter(
                Q(live_q(), is_hidden=False) | Q(created_by=self.request.user)
            )
        elif scope == 'live':
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
        if params.get('editor') and scope == 'all':
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
            return [IsAuthenticated(), ArticlePermission()]
        if getattr(self.request, 'method', None) == 'GET' or self.action in ('read',):
            return [AllowAny()]
        return [IsAuthenticated(), ArticlePermission()]

    def _check_write(self, serializer):
        """Refuse what the caller's permissions do not cover: staff-only fields
        for an author, and status moves (review and publishing are separate rights)."""
        user = self.request.user
        data = serializer.validated_data
        if not has_perm(user, 'change_article'):
            # Setting a field to the value it already has is not a change.
            fields = [
                name
                for name, default in STAFF_ONLY_FIELDS.items()
                if name in data
                and data[name]
                != (
                    getattr(serializer.instance, name)
                    if serializer.instance
                    else default
                )
            ]
            if fields:
                raise PermissionDenied(f'You cannot set: {", ".join(fields)}.')
        new = data.get('status')
        old = serializer.instance.status if serializer.instance else None
        if new is None or new == old or new in AUTHOR_SETS:
            return
        if new in PUBLISH_STATUSES:
            allowed = has_perm(user, 'publish_article')
        else:
            allowed = has_perm(user, 'review_article') or has_perm(
                user, 'publish_article'
            )
        if not allowed:
            raise PermissionDenied(f'You cannot move an article to {new}.')

    def perform_create(self, serializer):
        self._check_write(serializer)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._check_write(serializer)
        super().perform_update(serializer)

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
