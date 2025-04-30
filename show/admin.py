from django.contrib import admin

from show.models import Show, Theater, ShowTag


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
        'notes'
    ]


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    fields = ['name', 'capacity', 'location']


@admin.register(ShowTag)
class ShowTagAdmin(admin.ModelAdmin):
    fields = ['name']
