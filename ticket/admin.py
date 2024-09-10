from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget

from ticket.models import Theater


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    fields = ['name', 'capacity', 'location']
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }
