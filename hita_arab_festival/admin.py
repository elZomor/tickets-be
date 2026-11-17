from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ExportMixin
from import_export.formats.base_formats import XLSX

from hita_arab_festival.models.Application import Application
from hita_arab_festival.models.Article import Article
from hita_arab_festival.models.ArticleAttachment import ArticleAttachment
from hita_arab_festival.models.Comment import Comment
from hita_arab_festival.models.Festival import ArabFestival
from hita_arab_festival.models.Show import Show
from hita_arab_festival.models.Reservation import Reservation
from hita_arab_festival.models.Tag import Tag


@admin.register(ArabFestival)
class ArabFestivalAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_visible', 'applications_open')
    list_editable = ('is_visible', 'applications_open')


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    pass


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


@admin.register(Application)
class ApplicationAdmin(ExportMixin, admin.ModelAdmin):
    formats = [XLSX]
    list_display = (
        'show_name',
        'director_name',
        'department',
        'study_type',
        'mobile',
        'status',
        'created_at',
    )
    list_filter = ('festival', 'department', 'study_type', 'status')
    list_editable = ('status',)
    search_fields = ('show_name', 'director_name', 'email', 'mobile')
    readonly_fields = ('user', 'created_at', 'script_link', 'national_id_link')

    @staticmethod
    def _file_link(file_field):
        if not file_field:
            return '-'
        return format_html('<a href="{}" target="_blank">{}</a>', file_field.url, 'فتح')

    @admin.display(description='Script')
    def script_link(self, obj):
        return self._file_link(obj.script)

    @admin.display(description='National ID')
    def national_id_link(self, obj):
        return self._file_link(obj.national_id)
