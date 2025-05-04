from django.contrib import admin

from show.models import Show, Theater, ShowTag, Festival

from django.db import models
from django_json_widget.widgets import JSONEditorWidget

class ShowsInline(admin.StackedInline):
    model = Show
    can_delete = False
    verbose_name_plural = 'shows'
    extra = 0

@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    fields = ['name', 'capacity', 'location']


@admin.register(ShowTag)
class ShowTagAdmin(admin.ModelAdmin):
    fields = ['name']

@admin.register(Festival)
class FestivalAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }
    inlines = [ShowsInline]