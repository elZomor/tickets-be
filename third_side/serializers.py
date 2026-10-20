from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from third_side.i18n import LOCALES
from third_side.models.FestivalPost import (
    IMAGE_TYPES,
    VIDEO_TYPES,
    FestivalPostType,
)
from third_side.services.festivals import shown_translation
from third_side.services.media_urls import storage_url, to_key, to_url
from third_side.services.translations import sync_translations

from third_side.models import (
    Article,
    Category,
    Comment,
    Critic,
    FestivalPost,
    FestivalPostMedia,
    Rating,
    Report,
    Role,
    ThirdSideUser,
)
from third_side.models.Article import ArticleStatus


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'order']


class CriticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Critic
        fields = ['id', 'name', 'bio', 'photo']


class ArticleSerializer(serializers.ModelSerializer):
    """Editor writes. `doc` carries the per-language text in the shape the admin
    editor produces ({title, slug, content, isOriginalLanguage, aiGenerated}, each
    keyed by locale); it is upserted into ArticleTranslation, and the article's own
    title/slug follow its original language."""

    category_name = serializers.SerializerMethodField()
    critic_name = serializers.SerializerMethodField()
    editor = serializers.PrimaryKeyRelatedField(
        queryset=ThirdSideUser.objects.filter(role=Role.EDITOR),
        allow_null=True,
        required=False,
    )
    editor_name = serializers.SerializerMethodField()
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    doc = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'category_name',
            'critic',
            'critic_name',
            'editor',
            'editor_name',
            'cover_url',
            'content',
            'status',
            'published_at',
            'created_by',
            'is_hidden',
            'share_count',
            'doc',
        ]
        extra_kwargs = {'title': {'required': False}, 'slug': {'required': False}}

    def validate(self, attrs):
        doc = attrs.get('doc')
        if doc is not None:
            titles, slugs = doc.get('title') or {}, doc.get('slug') or {}
            ready = [lang for lang in LOCALES if titles.get(lang) and slugs.get(lang)]
            if not ready:
                raise serializers.ValidationError(
                    {'doc': 'At least one language needs a title and a slug.'}
                )
            ticks = doc.get('isOriginalLanguage') or {}
            original = next((lang for lang in ready if ticks.get(lang)), ready[0])
            attrs.setdefault('title', titles[original])
            attrs.setdefault('slug', slugs[original])
        elif self.instance is None and not (attrs.get('title') and attrs.get('slug')):
            raise serializers.ValidationError('A title and a slug are required.')
        self._check_publishing(attrs)
        slug = attrs.get('slug')
        if (
            slug
            and Article.objects.filter(slug=slug)
            .exclude(pk=getattr(self.instance, 'pk', None))
            .exists()
        ):
            raise serializers.ValidationError({'slug': 'This slug is already used.'})
        return attrs

    def validate_cover_url(self, value):
        return to_key(value)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['cover_url'] = to_url(data['cover_url'], self.context.get('request'))
        return data

    def _check_publishing(self, attrs):
        """Publishing stamps the time; scheduling needs a future time."""
        current = self.instance
        state = attrs.get('status', current.status if current else None)
        when = attrs.get('published_at', current.published_at if current else None)
        if state == ArticleStatus.PUBLISHED and when is None:
            attrs['published_at'] = timezone.now()
        elif state == ArticleStatus.SCHEDULED:
            if when is None:
                raise serializers.ValidationError(
                    {'published_at': 'Choose when to publish.'}
                )
            was_scheduled = current and current.status == ArticleStatus.SCHEDULED
            moved = current is None or current.published_at != when
            if when <= timezone.now() and (moved or not was_scheduled):
                raise serializers.ValidationError(
                    {'published_at': 'The scheduled time must be in the future.'}
                )

    @transaction.atomic
    def create(self, validated_data):
        doc = validated_data.pop('doc', None)
        article = super().create(validated_data)
        if doc:
            sync_translations(article, doc)
        return article

    @transaction.atomic
    def update(self, instance, validated_data):
        doc = validated_data.pop('doc', None)
        article = super().update(instance, validated_data)
        if doc:
            sync_translations(article, doc)
        return article

    @staticmethod
    def get_category_name(obj):
        return obj.category.name if obj.category else None

    @staticmethod
    def get_critic_name(obj):
        return obj.critic.name if obj.critic else None

    @staticmethod
    def get_editor_name(obj):
        return obj.editor.display_name if obj.editor else None


class RatingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Rating
        fields = ['id', 'user', 'article', 'value']


COMMENT_MAX_LENGTH = 2000


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    author_name = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'user',
            'author_name',
            'article',
            'text',
            'created_at',
            'is_hidden',
            'likes_count',
            'liked_by_me',
        ]
        read_only_fields = ['created_at', 'is_hidden']

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Comment cannot be empty')
        if len(value) > COMMENT_MAX_LENGTH:
            raise serializers.ValidationError(
                f'Comment is limited to {COMMENT_MAX_LENGTH} characters'
            )
        return value

    @staticmethod
    def get_author_name(obj) -> str:
        return obj.user.display_name

    @staticmethod
    def get_likes_count(obj) -> int:
        annotated = getattr(obj, 'likes_total', None)
        return annotated if annotated is not None else obj.likes.count()

    def get_liked_by_me(self, obj) -> bool:
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        liked = getattr(obj, 'liked_ids', None)
        if liked is not None:
            return obj.pk in liked
        return obj.likes.filter(user=user).exists()


class ReportSerializer(serializers.ModelSerializer):
    reporter = serializers.PrimaryKeyRelatedField(read_only=True)
    content_type = serializers.ChoiceField(
        choices=['article', 'comment'], write_only=True
    )
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id',
            'reporter',
            'content_type',
            'object_id',
            'target_type',
            'reason',
            'created_at',
            'reviewed_by',
            'reviewed_at',
        ]
        read_only_fields = ['reviewed_by', 'reviewed_at']

    @staticmethod
    def get_target_type(obj):
        return obj.content_type.model


class ProfileSerializer(serializers.ModelSerializer):
    """The signed-in reader: GET /profile/me."""

    name = serializers.SerializerMethodField()

    class Meta:
        model = ThirdSideUser
        fields = ['id', 'name', 'email', 'role']
        read_only_fields = fields

    @staticmethod
    def get_name(obj) -> str:
        return obj.display_name


def _clean_text_map(value, field):
    """{locale: text} with only the known locales and non-empty strings."""
    if value in (None, ''):
        return {}
    if not isinstance(value, dict):
        raise serializers.ValidationError({field: 'Expected {locale: text}.'})
    cleaned = {}
    for locale, text in value.items():
        if locale not in LOCALES:
            raise serializers.ValidationError({field: f'Unknown language "{locale}".'})
        if not isinstance(text, str):
            raise serializers.ValidationError({field: 'Texts must be strings.'})
        if text.strip():
            cleaned[locale] = text.strip()
    return cleaned


class FestivalPostMediaWriteSerializer(serializers.ModelSerializer):
    """One image of an image post; `image_url` comes from POST /media."""

    class Meta:
        model = FestivalPostMedia
        fields = ['image_url', 'alt_i18n', 'order']
        extra_kwargs = {'order': {'required': False}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        # Images uploaded through the Django admin have a file, not a URL.
        if not data['image_url'] and instance.image:
            data['image_url'] = storage_url(instance.image.name, request)
        data['image_url'] = to_url(data['image_url'], request)
        return data

    def validate_image_url(self, value):
        return to_key(value)

    def validate_alt_i18n(self, value):
        return _clean_text_map(value, 'alt_i18n')


class FestivalPostWriteSerializer(serializers.ModelSerializer):
    """Editor writes (and the editor's read via /festival-posts/<id>/doc).

    Only the fields that apply to the post's `type` are kept: switching type
    clears the rest, so a post never carries stale data.
    """

    media = FestivalPostMediaWriteSerializer(many=True, required=False)
    article_title = serializers.SerializerMethodField()

    class Meta:
        model = FestivalPost
        fields = [
            'id',
            'festival',
            'type',
            'published_at',
            'is_published',
            'original_language',
            'title_i18n',
            'body_i18n',
            'caption_i18n',
            'article',
            'article_title',
            'video_kind',
            'video_url',
            'poster_url',
            'media',
        ]

    def validate_poster_url(self, value):
        return to_key(value)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['poster_url'] = to_url(data['poster_url'], self.context.get('request'))
        return data

    def get_article_title(self, obj) -> str | None:
        if not obj.article_id:
            return None
        translation = shown_translation(obj.article, obj.original_language)
        return translation.title if translation else obj.article.title

    def _current(self, attrs, field, default=None):
        if field in attrs:
            return attrs[field]
        return getattr(self.instance, field, default) if self.instance else default

    def validate(self, attrs):
        kind = self._current(attrs, 'type')
        errors = {}
        for field in ('title_i18n', 'body_i18n', 'caption_i18n'):
            attrs[field] = _clean_text_map(self._current(attrs, field, {}), field)

        # Keep only what this type uses.
        if kind != FestivalPostType.TITLED_TEXT:
            attrs['title_i18n'] = {}
        if kind not in (FestivalPostType.TEXT, FestivalPostType.TITLED_TEXT):
            attrs['body_i18n'] = {}
        if kind not in (FestivalPostType.IMAGE_CAPTION, FestivalPostType.VIDEO_CAPTION):
            attrs['caption_i18n'] = {}
        if kind != FestivalPostType.ARTICLE:
            attrs['article'] = None
        if kind not in VIDEO_TYPES:
            attrs.update(video_kind='embed', video_url='', poster_url='')
        if kind not in IMAGE_TYPES:
            attrs['media'] = []

        if kind == FestivalPostType.TITLED_TEXT and not attrs['title_i18n']:
            errors['title_i18n'] = 'A titled text post needs a title.'
        if (
            kind in (FestivalPostType.TEXT, FestivalPostType.TITLED_TEXT)
            and not attrs['body_i18n']
        ):
            errors['body_i18n'] = 'A text post needs a body.'
        if kind in VIDEO_TYPES and not self._current(attrs, 'video_url', ''):
            errors['video_url'] = 'A video post needs a video URL.'
        if kind == FestivalPostType.ARTICLE and not attrs.get('article'):
            errors['article'] = 'An article post needs an article.'
        if kind in IMAGE_TYPES:
            media = attrs.get('media')
            if media is None and self.instance is not None:
                media = list(self.instance.media.all())
            if not media:
                errors['media'] = 'An image post needs at least one image.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    @staticmethod
    def _save_media(post, items):
        post.media.all().delete()
        FestivalPostMedia.objects.bulk_create(
            [
                FestivalPostMedia(
                    post=post,
                    image_url=item['image_url'],
                    alt_i18n=item.get('alt_i18n', {}),
                    order=item.get('order', index),
                )
                for index, item in enumerate(items)
            ]
        )

    @transaction.atomic
    def create(self, validated_data):
        media = validated_data.pop('media', [])
        post = super().create(validated_data)
        self._save_media(post, media)
        return post

    @transaction.atomic
    def update(self, instance, validated_data):
        media = validated_data.pop('media', None)
        post = super().update(instance, validated_data)
        if media is not None:
            self._save_media(post, media)
        return post
