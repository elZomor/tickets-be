import re

from django.core.exceptions import ValidationError
from django.db import models

from dynamic_forms.models.Form import Form


class FieldType(models.TextChoices):
    TEXT = 'TEXT', 'نص قصير'
    TEXTAREA = 'TEXTAREA', 'نص طويل'
    EMAIL = 'EMAIL', 'بريد إلكتروني'
    PHONE = 'PHONE', 'رقم هاتف'
    NUMBER = 'NUMBER', 'رقم'
    DATE = 'DATE', 'تاريخ'
    SELECT = 'SELECT', 'قائمة منسدلة'
    RADIO = 'RADIO', 'اختيار واحد'
    CHECKBOXES = 'CHECKBOXES', 'اختيار متعدد'
    CONSENT = 'CONSENT', 'إقرار (مربع واحد)'
    FILE = 'FILE', 'رفع ملف'


CHOICE_TYPES = {FieldType.SELECT, FieldType.RADIO, FieldType.CHECKBOXES}
TEXT_TYPES = {FieldType.TEXT, FieldType.TEXTAREA, FieldType.PHONE}


class FieldPreset(models.TextChoices):
    NONE = 'NONE', 'بدون'
    EGYPT_MOBILE = 'EGYPT_MOBILE', 'موبايل مصري'
    ARABIC_ONLY = 'ARABIC_ONLY', 'عربي فقط'


class FormField(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='fields')
    order = models.PositiveIntegerField(default=0)
    key = models.SlugField(
        max_length=64, help_text='Stable id for the answer (e.g. name, mobile).'
    )
    label = models.CharField(max_length=500)
    label_en = models.CharField(max_length=500, blank=True, default='')
    help_text = models.CharField(max_length=500, blank=True, default='')
    help_text_en = models.CharField(max_length=500, blank=True, default='')
    placeholder = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Input hint. For a consent field: the text beside the checkbox '
        '(the label is then shown above it as the rule being confirmed).',
    )
    placeholder_en = models.CharField(max_length=500, blank=True, default='')
    type = models.CharField(max_length=16, choices=FieldType.choices)
    required = models.BooleanField(default=True)
    options = models.JSONField(
        default=list,
        blank=True,
        help_text='Choices for dropdown / radio / multi-select, e.g. ["أ", "ب"].',
    )
    options_en = models.JSONField(
        default=list,
        blank=True,
        help_text='English display text for each option, in the same order '
        '(answers are always stored with the Arabic option).',
    )
    preset = models.CharField(
        max_length=16, choices=FieldPreset.choices, default=FieldPreset.NONE
    )
    pattern = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Optional regex the whole answer must match.',
    )
    min_length = models.PositiveIntegerField(null=True, blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    max_files = models.PositiveSmallIntegerField(default=1)
    allowed_extensions = models.JSONField(
        default=list,
        blank=True,
        help_text='File fields: e.g. [".jpg", ".png", ".pdf"]. Empty = any.',
    )
    max_file_mb = models.PositiveSmallIntegerField(default=10)

    class Meta:
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['form', 'key'], name='unique_form_field_key'
            ),
        ]

    def __str__(self):
        return f'{self.form} — {self.label}'

    @property
    def normalized_extensions(self):
        return [
            ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
            for ext in (self.allowed_extensions or [])
        ]

    def clean(self):
        if self.type in CHOICE_TYPES:
            if not isinstance(self.options, list) or not self.options:
                raise ValidationError({'options': 'Add at least one option.'})
            if not all(isinstance(o, str) and o.strip() for o in self.options):
                raise ValidationError({'options': 'Options must be non-empty text.'})
        if self.options_en:
            if not isinstance(self.options_en, list) or len(self.options_en) != len(
                self.options or []
            ):
                raise ValidationError(
                    {'options_en': 'Give one English option per option, or none.'}
                )
        if not isinstance(self.allowed_extensions, list):
            raise ValidationError({'allowed_extensions': 'Must be a list.'})
        if self.pattern:
            try:
                re.compile(self.pattern)
            except re.error as error:
                raise ValidationError({'pattern': f'Invalid regex: {error}'})
