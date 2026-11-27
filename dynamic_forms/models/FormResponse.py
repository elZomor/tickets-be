from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q

from dynamic_forms.models.Form import Form
from utils.code_utils import upload_to_form_response_file


class FormResponse(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='form_responses',
    )
    email = models.EmailField(blank=True, default='')
    answers = models.JSONField(default=dict)
    unique_value = models.CharField(
        max_length=255, blank=True, default='', db_index=True, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['form', 'unique_value'],
                condition=~Q(unique_value=''),
                name='unique_form_response_value',
            ),
        ]

    def __str__(self):
        return f'{self.form} #{self.pk}'


class ResponseFile(models.Model):
    response = models.ForeignKey(
        FormResponse, on_delete=models.CASCADE, related_name='files'
    )
    field_key = models.CharField(max_length=64)
    file = models.FileField(upload_to=upload_to_form_response_file, max_length=500)
    original_name = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.original_name or self.file.name
