from django.contrib import admin

from hita_arab_festival.models.Article import Article
from hita_arab_festival.models.ArticleAttachment import ArticleAttachment
from hita_arab_festival.models.Comment import Comment
from hita_arab_festival.models.Festival import ArabFestival
from hita_arab_festival.models.Show import Show
from hita_arab_festival.models.Reservation import Reservation
from hita_arab_festival.models.Tag import Tag


@admin.register(ArabFestival)
class ArabFestivalAdmin(admin.ModelAdmin):
    pass


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    pass


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    pass


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
