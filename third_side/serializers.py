from rest_framework import serializers

from third_side.models import (
    Article,
    Category,
    Comment,
    Critic,
    Profile,
    Rating,
    Report,
    SyncedArticle,
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


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'article', 'text', 'created_at', 'is_hidden']
        read_only_fields = ['created_at', 'is_hidden']


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
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'name', 'email', 'role']
        read_only_fields = ['role']

    def get_name(self, obj) -> str:
        user = obj.user
        return user.get_full_name().strip() or user.first_name or user.email


class SyncedArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncedArticle
        fields = '__all__'
