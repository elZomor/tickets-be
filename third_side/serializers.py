from rest_framework import serializers

from third_side.models import (
    Article,
    Category,
    Comment,
    Critic,
    Rating,
    Report,
    SyncedArticle,
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
    category_name = serializers.SerializerMethodField()
    critic_name = serializers.SerializerMethodField()
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

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
        ]

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


class SyncedArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncedArticle
        exclude = ('sync_status', 'sync_attempts', 'sync_error', 'last_attempt_at')
