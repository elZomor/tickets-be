from django.contrib import admin

from show.models import Show, Theater, ShowTag, Festival, Publication, ShowDate

from django.db import models
from django_json_widget.widgets import JSONEditorWidget

class ShowsInline(admin.StackedInline):
    model = Show
    can_delete = False
    verbose_name_plural = 'shows'
    extra = 0

class ShowDatesInline(admin.StackedInline):
    model = ShowDate
    can_delete = False
    verbose_name_plural = 'show_dates'
    extra = 1

class PublicationsInline(admin.StackedInline):
    model = Publication
    can_delete = False
    verbose_name_plural = 'publications'
    extra = 0

@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    inlines = [ShowDatesInline]


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    fields = ['name', 'capacity', 'location']


@admin.register(ShowTag)
class ShowTagAdmin(admin.ModelAdmin):
    fields = ['name']

@admin.register(Festival)
class FestivalAdmin(admin.ModelAdmin):
    pass

@admin.register(ShowDate)
class ShowDateAdmin(admin.ModelAdmin):
    pass

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    pass