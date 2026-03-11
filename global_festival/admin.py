from django.contrib import admin
from import_export.admin import ExportMixin
from import_export.formats.base_formats import XLSX

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
