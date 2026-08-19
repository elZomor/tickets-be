import secrets

from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ExportMixin
from import_export.formats.base_formats import XLSX

from config.constants import ALT_SPACES_FESTIVAL_FE_URL
from alt_spaces_festival.models.Article import Article
from alt_spaces_festival.models.ArticleAttachment import ArticleAttachment
from alt_spaces_festival.models.Comment import Comment
from alt_spaces_festival.models.Festival import AltSpacesFestival
from alt_spaces_festival.models.Publication import Publication
from alt_spaces_festival.models.Show import Show
from alt_spaces_festival.models.Reservation import Reservation
from alt_spaces_festival.models.Tag import Tag


class PublicationsInline(admin.StackedInline):
    model = Publication
    can_delete = False
    verbose_name_plural = 'publications'
    extra = 0


@admin.register(AltSpacesFestival)
class AltSpacesFestivalAdmin(admin.ModelAdmin):
    pass


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    pass


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    readonly_fields = ('reservation_link',)

    def reservation_link(self, obj):
        if not obj.pk or not obj.reservation_hash:
            return '—'
        url = f'{ALT_SPACES_FESTIVAL_FE_URL}/shows/{obj.pk}?token={obj.reservation_hash}'
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
