from django.db import transaction
from rest_framework import serializers

from third_side.i18n import LOCALES
from third_side.services.translations import sync_translations

from third_side.models import (
    Article,
    Category,
    Comment,
    Critic,
    Rating,
    Report,
    ThirdSideUser,
)


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
        slug = attrs.get('slug')
        if (
            slug
            and Article.objects.filter(slug=slug)
            .exclude(pk=getattr(self.instance, 'pk', None))
            .exists()
        ):
            raise serializers.ValidationError({'slug': 'This slug is already used.'})
        return attrs

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
