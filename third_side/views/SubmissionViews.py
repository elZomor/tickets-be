import uuid

from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from third_side.auth import ThirdSideJWTAuthentication
from third_side.i18n import LOCALE_CHOICES, clean_locale, localize, slugify_name
from third_side.models import Article, Category, Critic, Media
from third_side.models.Article import ArticleStatus
from third_side.services.media_urls import file_url
from third_side.services.translations import pick_locale, translation_map

MIN_CONTENT = 100
MAX_CONTENT = 50_000
MAX_IMAGES = 10

# What the reader sees: the editorial workflow collapses to three states.
SUBMISSION_STATUS = {
    ArticleStatus.PUBLISHED: 'published',
    ArticleStatus.REJECTED: 'rejected',
    ArticleStatus.ARCHIVED: 'rejected',
}


def submission_status(article_status):
    return SUBMISSION_STATUS.get(article_status, 'pending')


class SubmissionCreateSerializer(serializers.Serializer):
    category_slug = serializers.SlugField(allow_unicode=True)
    title = serializers.CharField(min_length=3, max_length=255)
    language = serializers.ChoiceField(choices=LOCALE_CHOICES)
    content = serializers.CharField(min_length=MIN_CONTENT, max_length=MAX_CONTENT)
    allow_translation = serializers.BooleanField(default=True)
    # Ids from POST /media, uploaded by the same reader.
    images = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        max_length=MAX_IMAGES,
        required=False,
        default=list,
    )

    def validate_images(self, value):
        ids = list(dict.fromkeys(value))
        user = self.context['request'].user
        found = Media.objects.filter(pk__in=ids, uploaded_by=user)
        if found.count() != len(ids):
            raise serializers.ValidationError('Unknown image')
        return ids

    def validate_title(self, value):
        return value.strip()

    def validate_content(self, value):
        value = value.strip()
        if len(value) < MIN_CONTENT:
            raise serializers.ValidationError(
                f'Content must be at least {MIN_CONTENT} characters'
            )
        return value

    def validate_category_slug(self, value):
        category = Category.objects.filter(slug=value).first()
        if category is None:
            raise serializers.ValidationError('Unknown category')
        self.context['category'] = category
        return value


class SubmissionSerializer(serializers.ModelSerializer):
    group_id = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    category_slug = serializers.CharField(source='category.slug')
    category_name = serializers.SerializerMethodField()
    language = serializers.CharField(source='original_language')
    status = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    category_url_slug = serializers.SerializerMethodField()
    group_url_slug = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id',
            'group_id',
            'group_name',
            'category_slug',
            'category_name',
            'category_url_slug',
            'group_url_slug',
            'slug',
            'title',
            'language',
            'content',
            'allow_translation',
            'images',
            'status',
            'created_at',
        ]

    def _lang(self):
        request = self.context.get('request')
        return clean_locale(request.query_params.get('lang') if request else None)

    def get_group_id(self, obj) -> str | None:
        return obj.category.group.slug if obj.category.group else None

    def get_group_name(self, obj) -> str:
        group = obj.category.group
        return localize(group.label, self._lang(), group.slug) if group else ''

    def get_category_name(self, obj) -> str:
        return localize(obj.category.name_i18n, self._lang(), obj.category.name)

    def get_images(self, obj) -> list[str]:
        request = self.context.get('request')
        media = sorted(obj.submitted_media.all(), key=lambda item: item.pk)
        return [file_url(item.file.name, request) for item in media]

    def get_status(self, obj) -> str:
        return submission_status(obj.status)

    # With the localized category/group segments, enough to build the
    # article's public address: /<lang>[/<group>]/<category>/<slug>.
    def get_slug(self, obj) -> str:
        translations = translation_map(obj)
        locale = pick_locale(translations, self._lang(), obj.original_language)
        return translations[locale]['slug']

    def get_category_url_slug(self, obj) -> str:
        return localize(obj.category.url_slug, self._lang(), obj.category.slug)

    def get_group_url_slug(self, obj) -> str | None:
        group = obj.category.group
        return localize(group.url_slug, self._lang(), group.slug) if group else None


def _writer_for(user):
    """The Critic profile a reader's submissions are filed under."""
    critic = Critic.objects.filter(user=user).first()
    if critic:
        return critic
    name = user.display_name
    critic = Critic.objects.create(user=user, name=name)
    base = slugify_name(name) or 'writer'
    critic.name_i18n = {code: name for code, _ in LOCALE_CHOICES}
    critic.slug_i18n = {code: f'{base}-{critic.pk}' for code, _ in LOCALE_CHOICES}
    critic.save(update_fields=['name_i18n', 'slug_i18n'])
    return critic


class SubmissionsView(GenericAPIView):
    """POST: send an article for review. GET: the signed-in reader's own."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SubmissionSerializer

    @property
    def throttle_scope(self):
        return (
            'third_side_submit'
            if getattr(self.request, 'method', None) == 'POST'
            else 'third_side_write'
        )

    def get(self, request):
        articles = (
            # Articles the reader sent in, plus ones an editor attached to
            # their writer profile (those have no created_by).
            Article.objects.filter(
                Q(created_by=request.user) | Q(critic__user=request.user)
            )
            .select_related('category', 'category__group')
            .prefetch_related('translations', 'submitted_media')
            .distinct()
            .order_by('-created_at', '-id')
        )
        page = self.paginate_queryset(articles)
        data = SubmissionSerializer(page, many=True, context={'request': request}).data
        return self.get_paginated_response(data)

    def post(self, request):
        serializer = SubmissionCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        category = serializer.context['category']
        slug = f"{slugify(data['title'], allow_unicode=True)[:200] or 'article'}-{uuid.uuid4().hex[:8]}"
        with transaction.atomic():
            article = Article.objects.create(
                title=data['title'],
                slug=slug,
                category=category,
                critic=_writer_for(request.user),
                content=data['content'],
                status=ArticleStatus.SUBMITTED,
                original_language=data['language'],
                allow_translation=data['allow_translation'],
                created_by=request.user,
                via_website=True,
            )
            article.submitted_media.set(data['images'])
        return Response(
            SubmissionSerializer(article, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
