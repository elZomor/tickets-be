import secrets

from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ExportMixin
from import_export.formats.base_formats import XLSX

from config.constants import GLOBAL_FESTIVAL_FE_URL
from global_festival.models.Article import Article
from global_festival.models.ArticleAttachment import ArticleAttachment
from global_festival.models.Comment import Comment
from global_festival.models.Festival import GlobalFestival
from global_festival.models.Show import Show
from global_festival.models.Reservation import Reservation
from global_festival.models.Tag import Tag


@admin.register(GlobalFestival)
class GlobalFestivalAdmin(admin.ModelAdmin):
    pass


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    readonly_fields = ('reservation_link',)

    def reservation_link(self, obj):
        if not obj.pk or not obj.reservation_hash:
            return '—'
        url = f'{GLOBAL_FESTIVAL_FE_URL}/shows/{obj.pk}?token={obj.reservation_hash}'
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)

    reservation_link.short_description = 'Reservation Link'

    def save_model(self, request, obj, form, change):
        if not obj.reservation_hash:
            obj.reservation_hash = secrets.token_hex(16)
        super().save_model(request, obj, form, change)


@admin.register(Reservation)
class ReservationAdmin(ExportMixin, admin.ModelAdmin):
    formats = [XLSX]
    list_filter = ('show__name',)


class ArticleAttachmentInline(admin.StackedInline):
    model = ArticleAttachment
    extra = 0


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    inlines = [ArticleAttachmentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    pass


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass
