from django.contrib import admin
from django.db import models
from django_json_widget.widgets import JSONEditorWidget

from third_side.models import (
    AboutPage,
    Ad,
    Article,
    ArticleTranslation,
    Category,
    Comment,
    CommentLike,
    Critic,
    NavGroup,
    Profile,
    SiteSettings,
    Rating,
    Report,
    SyncedArticle,
    Tag,
)


class JsonFieldsAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {'widget': JSONEditorWidget}}


@admin.register(NavGroup)
class NavGroupAdmin(JsonFieldsAdmin):
    list_display = ('slug', 'order')


@admin.register(Tag)
class TagAdmin(JsonFieldsAdmin):
    list_display = ('slug',)


class ArticleTranslationInline(admin.StackedInline):
    model = ArticleTranslation
    extra = 0
    formfield_overrides = {models.JSONField: {'widget': JSONEditorWidget}}


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')


@admin.register(Category)
class CategoryAdmin(JsonFieldsAdmin):
    list_display = ('name', 'slug', 'group', 'order', 'show_in_nav', 'featured')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Critic)
class CriticAdmin(JsonFieldsAdmin):
    list_display = ('name',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'critic',
        'status',
        'is_hidden',
        'published_at',
    )
    list_filter = ('status', 'category', 'is_hidden', 'original_language')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ArticleTranslationInline]
    filter_horizontal = ('tags',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'value')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at', 'is_hidden')
    list_filter = ('is_hidden',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'reporter',
        'content_type',
        'object_id',
        'created_at',
        'reviewed_by',
    )
    list_filter = ('content_type',)
    readonly_fields = ('created_at',)


@admin.register(SyncedArticle)
class SyncedArticleAdmin(admin.ModelAdmin):
    list_display = ('payload_id', 'article', 'updated_at')
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(SiteSettings)
class SiteSettingsAdmin(JsonFieldsAdmin):
    list_display = ('__str__',)


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment', 'created_at')


@admin.register(AboutPage)
class AboutPageAdmin(JsonFieldsAdmin):
    list_display = ('__str__',)


@admin.register(Ad)
class AdAdmin(JsonFieldsAdmin):
    list_display = (
        'name',
        'type',
        'is_active',
        'starts_at',
        'ends_at',
        'weight',
        'impressions',
        'clicks',
    )
    list_filter = ('type', 'is_active')
    readonly_fields = ('impressions', 'clicks')
