"""A reader's saved articles and follows."""

from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.auth import ThirdSideJWTAuthentication
from third_side.i18n import clean_locale, localize
from third_side.models import (
    Article,
    Category,
    Critic,
    Festival,
    Follow,
    NavGroup,
    SavedArticle,
)
from third_side.models.Article import live_q
from third_side.models.Follow import FollowTarget
from third_side.read_serializers import ArticleReadSerializer
from third_side.services.festivals import article_path, shown_translation


def _readable_articles():
    return Article.objects.filter(live_q(), is_hidden=False)


class SavedArticleSerializer(ArticleReadSerializer):
    """The article card plus its frontend address in the requested language."""

    path = serializers.SerializerMethodField()

    class Meta(ArticleReadSerializer.Meta):
        fields = ArticleReadSerializer.Meta.fields + ['path']

    def get_path(self, obj) -> str:
        request = self.context.get('request')
        lang = clean_locale(request.query_params.get('lang') if request else None)
        return article_path(obj, lang, shown_translation(obj, lang))


class SavedArticlesView(GenericAPIView):
    """GET saved-articles: the user's saved articles (cards, ?lang=), newest first."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SavedArticleSerializer
    throttle_scope = 'third_side_read'

    def get(self, request):
        queryset = (
            _readable_articles()
            .filter(saved_by__user=request.user)
            .select_related('category', 'critic', 'editor')
            .prefetch_related('translations', 'tags')
            .annotate(
                rating_avg=Avg('ratings__value'),
                rating_count=Count('ratings', distinct=True),
            )
            .order_by('-saved_by__created_at', '-id')
        )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class SavedArticleIdsView(APIView):
    """GET saved-articles/ids: every saved id, so buttons know their state."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_read'

    def get(self, request):
        ids = SavedArticle.objects.filter(user=request.user).values_list(
            'article_id', flat=True
        )
        return Response({'ids': list(ids)})


class SavedArticleView(APIView):
    """PUT saved-articles/{id} saves an article, DELETE forgets it (both idempotent)."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_write'

    def put(self, request, article_id):
        article = get_object_or_404(_readable_articles(), pk=article_id)
        _, created = SavedArticle.objects.get_or_create(
            user=request.user, article=article
        )
        return Response(
            {'saved': True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, article_id):
        SavedArticle.objects.filter(user=request.user, article_id=article_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


TARGET_MODELS = {
    FollowTarget.CRITIC: Critic,
    FollowTarget.CATEGORY: Category,
    FollowTarget.NAVGROUP: NavGroup,
    FollowTarget.FESTIVAL: Festival,
}


def target_name(target_type, target, lang):
    """Display name of a followed thing in `lang`."""
    if target_type == FollowTarget.NAVGROUP:
        return localize(target.label, lang, target.slug)
    return localize(
        target.name_i18n, lang, target.name if hasattr(target, 'name') else target.slug
    )


class FollowSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = ['target_type', 'target_id', 'slug', 'name', 'created_at']

    def get_slug(self, obj) -> str:
        return getattr(
            self.context['targets'].get((obj.target_type, obj.target_id)), 'slug', ''
        )

    def get_name(self, obj) -> str:
        target = self.context['targets'].get((obj.target_type, obj.target_id))
        if target is None:
            return ''
        return target_name(obj.target_type, target, self.context['lang'])


class FollowsView(GenericAPIView):
    """GET follows (?lang=): everything the user follows, newest first."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer
    throttle_scope = 'third_side_read'
    pagination_class = None

    def get(self, request):
        follows = list(Follow.objects.filter(user=request.user))
        targets = {}
        for target_type, model in TARGET_MODELS.items():
            ids = {f.target_id for f in follows if f.target_type == target_type}
            for target in model.objects.filter(pk__in=ids):
                targets[(target_type, target.pk)] = target
        lang = clean_locale(request.query_params.get('lang'))
        data = FollowSerializer(
            follows, many=True, context={'targets': targets, 'lang': lang}
        ).data
        return Response(data)


def find_target(target_type, ref):
    """The followed object: `ref` is its id, or its slug where it has one."""
    model = TARGET_MODELS.get(target_type)
    if model is None:
        return None
    if ref.isdigit():
        return model.objects.filter(pk=int(ref)).first()
    if hasattr(model, 'slug'):
        return model.objects.filter(slug=ref).first()
    return None


class FollowView(APIView):
    """PUT follows/{type}/{id or slug} follows, DELETE unfollows (both idempotent)."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_write'

    def put(self, request, target_type, target_ref):
        target = find_target(target_type, target_ref)
        if target is None:
            return Response({'detail': 'Unknown target'}, status=404)
        _, created = Follow.objects.get_or_create(
            user=request.user, target_type=target_type, target_id=target.pk
        )
        return Response(
            {'following': True, 'target_id': target.pk},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, target_type, target_ref):
        target = find_target(target_type, target_ref)
        if target is not None:
            Follow.objects.filter(
                user=request.user, target_type=target_type, target_id=target.pk
            ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
