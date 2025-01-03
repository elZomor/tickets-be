from django.contrib import admin
from django_celery_results.models import TaskResult

admin.site.unregister(TaskResult)
@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ('date_done', 'result', 'task_kwargs')
    list_filter = ('status', 'date_done')
    search_fields = ('task_id', 'result')
    readonly_fields = ('task_id', 'status', 'date_done', 'result', 'traceback', 'meta', 'task_name')

    fieldsets = (
        (None, {
            'fields': ('task_id', 'task_name', 'status', 'date_done')
        }),
        ('Result Information', {
            'fields': ('result', 'traceback', 'meta')
        }),
    )