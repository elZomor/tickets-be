from django.contrib import admin

from eldorg.models import Script


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    pass
