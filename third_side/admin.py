from django import forms
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
    SiteSettings,
    Rating,
    Report,
    SyncedArticle,
    Tag,
    TermsAcceptance,
    TermsVersion,
    ThirdSideUser,
)
from third_side.models.SyncedArticle import PayloadSyncStatus


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


class ThirdSideUserForm(forms.ModelForm):
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        help_text='Leave blank to keep the current password.',
    )

    class Meta:
        model = ThirdSideUser
        fields = ('email', 'name', 'role', 'is_active', 'new_password')


@admin.register(ThirdSideUser)
class ThirdSideUserAdmin(admin.ModelAdmin):
    form = ThirdSideUserForm
    list_display = ('email', 'name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('email', 'name')

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get('new_password')
        if password:
            obj.set_password(password)
        elif not change:
            obj.set_unusable_password()
        super().save_model(request, obj, form, change)


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
    list_display = (
        'payload_id',
        'article',
        'sync_status',
        'sync_attempts',
        'last_attempt_at',
        'updated_at',
    )
    list_filter = ('sync_status',)
    readonly_fields = ('sync_attempts', 'sync_error', 'last_attempt_at')
    actions = ['retry_push_to_payload']
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }

    @admin.action(description='Retry push to Payload')
    def retry_push_to_payload(self, request, queryset):
        from third_side.services.payload_sync import enqueue_push

        pending = queryset.exclude(sync_status=PayloadSyncStatus.SYNCED).filter(
            article__isnull=False
        )
        for synced in pending:
            synced.sync_status = PayloadSyncStatus.PENDING
            synced.save(update_fields=['sync_status', 'updated_at'])
            enqueue_push(synced.pk)
        self.message_user(request, f'Queued {pending.count()} article(s) for Payload.')


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


@admin.register(TermsVersion)
class TermsVersionAdmin(JsonFieldsAdmin):
    list_display = ('version', 'effective_date', 'is_published', 'created_at')
    list_filter = ('is_published',)

    def get_readonly_fields(self, request, obj=None):
        # A published version is what users accepted: publish a new one instead.
        if obj is not None and obj.is_published:
            return ('version', 'effective_date', 'is_published', 'content')
        return ()

    def has_delete_permission(self, request, obj=None):
        return obj is None or not obj.is_published


@admin.register(TermsAcceptance)
class TermsAcceptanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'terms', 'accepted_at', 'ip_address')
    list_filter = ('terms',)
    readonly_fields = ('user', 'terms', 'accepted_at', 'ip_address')

    def has_add_permission(self, request):
        return False
