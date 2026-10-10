from django.contrib import admin
from django.db import models
from django_json_widget.widgets import JSONEditorWidget

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


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Critic)
class CriticAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'critic', 'status', 'is_hidden', 'published_at')
    list_filter = ('status', 'category', 'is_hidden')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'value')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at', 'is_hidden')
    list_filter = ('is_hidden',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'content_type', 'object_id', 'created_at', 'reviewed_by')
    list_filter = ('content_type',)
    readonly_fields = ('created_at',)


@admin.register(SyncedArticle)
class SyncedArticleAdmin(admin.ModelAdmin):
    list_display = ('payload_id', 'updated_at')
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }
