from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget

from ticket.models import Theater, Performance, Reservation


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    fields = ['name', 'capacity', 'location']
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    fields = ['name', 'link', 'time', 'theater', 'initial_reserved_seats', 'remaining_seats']
    readonly_fields = ['remaining_seats']
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    fields = ['name', 'email', 'performance',
              'link_delivered', 'guest_arrived', 'created_at', 'updated_at']
    readonly_fields = ['name', 'email', 'performance',
              'link_delivered', 'guest_arrived', 'created_at', 'updated_at']
