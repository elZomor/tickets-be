from django.contrib import admin

from ai.models import PerformerInsights


@admin.register(PerformerInsights)
class PerformerInsightsAdmin(admin.ModelAdmin):
    pass
