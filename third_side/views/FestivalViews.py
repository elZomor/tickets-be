from django.db.models import Count, Q
from django.http import Http404
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import Festival, FestivalPost
from third_side.models.Article import ArticleStatus
from third_side.models.FestivalPost import FestivalPostType
from third_side.permissions import IsEditor, is_editor
from third_side.read_serializers import (
    FestivalPostReadSerializer,
    FestivalReadSerializer,
)
from third_side.serializers import FestivalPostWriteSerializer


class _PublicReadViewSet(GenericViewSet):
    """Public, read-only: no auth. Content is managed in the Django admin."""

    authentication_classes = []
    permission_classes = [AllowAny]


class FestivalViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, _PublicReadViewSet
):
    """Festival cards, localized with ?lang=. GET /festivals/by-slug/<slug> takes
    the URL segment of any locale."""

    serializer_class = FestivalReadSerializer

    def get_queryset(self):
        return Festival.objects.annotate(
            posts_count=Count('posts', filter=Q(posts__is_published=True))
        ).order_by('-starts_on', '-id')

    @action(detail=False, methods=['get'], url_path=r'by-slug/(?P<slug>[^/]+)')
    def by_slug(self, request, slug=None):
        for festival in self.get_queryset():
            if slug == festival.slug or slug in festival.slug_i18n.values():
                return Response(self.get_serializer(festival).data)
        raise Http404


class FestivalPostViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """The feed, newest first. ?festival=<id> limits it to one festival.

    Reads are public. Editors (the admin panel) also see unpublished posts and
    write with the plain serializer; GET /festival-posts/<id>/doc returns one
    post in the shape the admin form edits.
    """

    authentication_classes = [ThirdSideJWTAuthentication]

    def get_serializer_class(self):
        if getattr(self.request, 'method', None) == 'GET' and self.action == 'list':
            return FestivalPostReadSerializer
        return FestivalPostWriteSerializer

    def get_permissions(self):
        if self.action == 'doc' or getattr(self.request, 'method', None) != 'GET':
            return [IsAuthenticated(), IsEditor()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = (
            FestivalPost.objects.select_related('festival', 'article__category__group')
            .prefetch_related('media', 'article__translations')
            .order_by('-published_at', '-id')
        )
        festival = self.request.query_params.get('festival')
        if festival and festival.isdigit():
            queryset = queryset.filter(festival_id=int(festival))
        if is_editor(self.request.user):
            return queryset
        queryset = queryset.filter(is_published=True)
        # An article post whose article is gone, hidden or not published yet
        # would render empty.
        return queryset.exclude(
            Q(type=FestivalPostType.ARTICLE)
            & (
                Q(article__isnull=True)
                | Q(article__is_hidden=True)
                | ~Q(article__status=ArticleStatus.PUBLISHED)
            )
        )

    @action(detail=True, methods=['get'])
    def doc(self, request, pk=None):
        """Editor-only: the post as the admin form edits it."""
        return Response(self.get_serializer(self.get_object()).data)
