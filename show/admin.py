from django.contrib import admin

from show.models import Show, Theater, ShowTag, Festival


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    fields = [
        'name',
        'link',
        'time',
        'author',
        'director',
        'theater',
        'created_by',
        'reviewed_by',
        'status',
        'poster',
        'tags',
        'cast_name',
        'cast',
        'crew',
        'notes',
        'festival'
    ]


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    fields = ['name', 'capacity', 'location']


@admin.register(ShowTag)
class ShowTagAdmin(admin.ModelAdmin):
    fields = ['name']

@admin.register(Festival)
class FestivalAdmin(admin.ModelAdmin):
    pass