from io import BytesIO

from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.text import slugify
from openpyxl import Workbook

from dynamic_forms.models import FieldType, Form, FormField, FormResponse


class LinesField(forms.CharField):
    """Edit a JSON list of strings as one item per line."""

    widget = forms.Textarea(attrs={'rows': 4, 'cols': 40})

    def prepare_value(self, value):
        if isinstance(value, list):
            return '\n'.join(str(v) for v in value)
        return value

    def to_python(self, value):
        if isinstance(value, list):
            return value
        return [line.strip() for line in (value or '').splitlines() if line.strip()]


class FormFieldAdminForm(forms.ModelForm):
    options = LinesField(
        required=False,
        help_text='One option per line (dropdown / radio / multi-select).',
    )
    options_en = LinesField(
        required=False,
        help_text='English text for each option, same order (optional).',
    )
    allowed_extensions = LinesField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'cols': 20}),
        help_text='File fields: one per line, e.g. .jpg — empty allows any type.',
    )

    class Meta:
        model = FormField
        fields = '__all__'


class FormFieldInline(admin.StackedInline):
    model = FormField
    form = FormFieldAdminForm
    extra = 0
    fieldsets = (
        (None, {'fields': (('order', 'key', 'type', 'required'), 'label')}),
        ('Text & choices', {'fields': ('help_text', 'placeholder', 'options')}),
        (
            'English',
            {
                'classes': ('collapse',),
                'fields': ('label_en', 'help_text_en', 'placeholder_en', 'options_en'),
            },
        ),
        (
            'Validation',
            {
                'classes': ('collapse',),
                'fields': (
                    ('preset', 'pattern'),
                    ('min_length', 'max_length'),
                    ('max_files', 'max_file_mb'),
                    'allowed_extensions',
                ),
            },
        ),
    )


def _cell(field, response):
    if field.type == FieldType.FILE:
        return '\n'.join(
            f.file.url for f in response.files.all() if f.field_key == field.key
        )
    value = response.answers.get(field.key, '')
    if isinstance(value, list):
        return '، '.join(value)
    if isinstance(value, bool):
        return 'نعم' if value else 'لا'
    return value


def build_workbook(forms_with_responses):
    workbook = Workbook()
    workbook.remove(workbook.active)
    for form, responses in forms_with_responses:
        sheet = workbook.create_sheet(slugify(form.slug, allow_unicode=True)[:31])
        sheet.sheet_view.rightToLeft = True
        fields = list(form.fields.all())
        sheet.append(['التاريخ', 'البريد'] + [f.label for f in fields])
        for response in responses:
            sheet.append(
                [
                    timezone.localtime(response.created_at).strftime('%Y-%m-%d %H:%M'),
                    response.email,
                ]
                + [_cell(f, response) for f in fields]
            )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def xlsx_response(content, name):
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{name}.xlsx"'
    return response


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'festival_name',
        'slug',
        'is_active',
        'open_state',
        'responses_count',
        'requires_login',
        'created_at',
    )
    list_filter = (
        'is_active',
        'requires_login',
        'arab_festival',
        'global_festival',
        'alt_spaces_festival',
    )
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [FormFieldInline]
    actions = ['duplicate_forms', 'export_responses']
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'description', 'notice', 'warning')}),
        (
            'English',
            {
                'classes': ('collapse',),
                'fields': (
                    'title_en',
                    'description_en',
                    'notice_en',
                    'warning_en',
                    'success_message_en',
                ),
            },
        ),
        (
            'Festival (choose exactly one)',
            {'fields': ('arab_festival', 'global_festival', 'alt_spaces_festival')},
        ),
        (
            'Availability',
            {'fields': ('is_active', ('opens_at', 'closes_at'), 'max_responses')},
        ),
        (
            'Who can submit',
            {'fields': ('requires_login', ('unique_by', 'unique_field_key'))},
        ),
        ('After submit', {'fields': ('success_message',)}),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('arab_festival', 'global_festival', 'alt_spaces_festival')
            .annotate(_responses=Count('responses'))
        )

    @admin.display(description='Festival')
    def festival_name(self, obj):
        return obj.festival or '-'

    @admin.display(description='Responses', ordering='_responses')
    def responses_count(self, obj):
        return obj._responses

    @admin.display(description='State')
    def open_state(self, obj):
        return obj.closed_reason(obj._responses) or 'OPEN'

    @admin.action(description='Duplicate selected forms (with fields)')
    def duplicate_forms(self, request, queryset):
        for form in queryset:
            fields = list(form.fields.all())
            with transaction.atomic():
                form.pk = None
                form.slug = self._free_slug(form.slug)
                form.title = f'{form.title} (نسخة)'
                form.is_active = False
                form.save()
                for field in fields:
                    field.pk = None
                    field.form = form
                    field.save()
        self.message_user(
            request, 'Copies created as inactive forms.', messages.SUCCESS
        )

    @staticmethod
    def _free_slug(slug):
        index = 2
        while Form.objects.filter(slug=f'{slug}-{index}').exists():
            index += 1
        return f'{slug}-{index}'

    @admin.action(description='Export responses (Excel)')
    def export_responses(self, request, queryset):
        data = [
            (form, form.responses.prefetch_related('files'))
            for form in queryset.prefetch_related('fields')
        ]
        return xlsx_response(build_workbook(data), 'form-responses')

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        obj = form.instance
        keys = set(obj.fields.values_list('key', flat=True))
        if obj.unique_field_key and obj.unique_field_key not in keys:
            self.message_user(
                request,
                f'"{obj.unique_field_key}" is not a field key of this form, '
                'so duplicate responses are not being blocked.',
                messages.WARNING,
            )


@admin.register(FormResponse)
class FormResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'form', 'email', 'summary', 'created_at')
    list_filter = ('form',)
    search_fields = ('email', 'answers', 'unique_value')
    readonly_fields = ('form', 'user', 'email', 'created_at', 'answers_table')
    exclude = ('answers',)
    actions = ['export_selected']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('form')

    def has_add_permission(self, request):
        return False

    @admin.display(description='Answers')
    def summary(self, obj):
        values = [v for v in obj.answers.values() if isinstance(v, str) and v]
        return ' · '.join(values[:3])

    @admin.display(description='Answers')
    def answers_table(self, obj):
        rows = []
        for field in obj.form.fields.all():
            if field.type == FieldType.FILE:
                links = format_html_join(
                    ' ',
                    '<a href="{}" target="_blank">{}</a>',
                    (
                        (f.file.url, f.original_name or 'فتح')
                        for f in obj.files.all()
                        if f.field_key == field.key
                    ),
                )
                rows.append((field.label, links or '-'))
            else:
                rows.append((field.label, _cell(field, obj) or '-'))
        return format_html(
            '<table>{}</table>',
            format_html_join(
                '', '<tr><th style="text-align:start">{}</th><td>{}</td></tr>', rows
            ),
        )

    @admin.action(description='Export selected responses (Excel)')
    def export_selected(self, request, queryset):
        grouped = {}
        for response in queryset.select_related('form').prefetch_related('files'):
            grouped.setdefault(response.form, []).append(response)
        return xlsx_response(build_workbook(grouped.items()), 'form-responses')
