from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from dynamic_forms.models import FieldType, Form, FormResponse, ResponseFile, UniqueBy
from dynamic_forms.validation import validate_answers
from utils.Response import (
    get_already_exists_response,
    get_bad_request_response,
    get_successful_creation_response,
    get_successful_response,
    get_unauthorized_response,
)


def serialize_field(field):
    data = {
        'key': field.key,
        'label': field.label,
        'help_text': field.help_text,
        'placeholder': field.placeholder,
        'type': field.type,
        'required': field.required,
        'preset': field.preset,
        'pattern': field.pattern,
        'min_length': field.min_length,
        'max_length': field.max_length,
    }
    if field.type in (FieldType.SELECT, FieldType.RADIO, FieldType.CHECKBOXES):
        data['options'] = field.options
    if field.type == FieldType.FILE:
        data['max_files'] = field.max_files
        data['allowed_extensions'] = field.normalized_extensions
        data['max_file_mb'] = field.max_file_mb
    return data


def find_my_response(form, user):
    if not user.is_authenticated:
        return None
    response = form.responses.filter(user=user).first()
    if not response:
        return None
    return {'id': response.id, 'created_at': response.created_at}


def unique_value_for(form, user, answers):
    """Normalized value that must not repeat within the form ('' = no check)."""
    if form.unique_by == UniqueBy.USER and user.is_authenticated:
        return f'user:{user.id}'
    if form.unique_by == UniqueBy.FIELD and form.unique_field_key:
        value = answers.get(form.unique_field_key)
        if isinstance(value, str) and value:
            return f'{form.unique_field_key}:{value.lower()}'[:255]
    return ''


def festival_forms(festival_field):
    """Forms of the festival app whose URL prefix the request came through."""
    return Form.objects.filter(**{f'{festival_field}__isnull': False})


class FormDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug, festival_field):
        form = get_object_or_404(
            festival_forms(festival_field).annotate(response_count=Count('responses')),
            slug=slug,
        )
        closed_reason = form.closed_reason(form.response_count)
        return get_successful_response(
            data={
                'slug': form.slug,
                'title': form.title,
                'description': form.description,
                'notice': form.notice,
                'success_message': form.success_message,
                'requires_login': form.requires_login
                or form.unique_by == UniqueBy.USER,
                'opens_at': form.opens_at,
                'closes_at': form.closes_at,
                'open': closed_reason is None,
                'closed_reason': closed_reason,
                'fields': [serialize_field(f) for f in form.fields.all()],
                'my_response': find_my_response(form, request.user),
            }
        )


class FormSubmitView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = 'forms_submit'

    def post(self, request, slug, festival_field):
        form = get_object_or_404(festival_forms(festival_field), slug=slug)
        user = request.user

        needs_login = form.requires_login or form.unique_by == UniqueBy.USER
        if needs_login and not user.is_authenticated:
            return get_unauthorized_response(message='LOGIN_REQUIRED')
        if form.closed_reason():
            return get_bad_request_response(message='FORM_CLOSED')

        fields = list(form.fields.all())
        answers, uploads, errors = validate_answers(fields, request.data, request.FILES)
        if errors:
            return get_bad_request_response(data=errors, message='VALIDATION_ERROR')

        unique_value = unique_value_for(form, user, answers)
        try:
            with transaction.atomic():
                # Lock the form row so the response cap can't be exceeded.
                locked = Form.objects.select_for_update().get(pk=form.pk)
                if locked.closed_reason():
                    return get_bad_request_response(message='FORM_CLOSED')
                if (
                    unique_value
                    and locked.responses.filter(unique_value=unique_value).exists()
                ):
                    return get_already_exists_response(message='ALREADY_SUBMITTED')

                response = FormResponse.objects.create(
                    form=locked,
                    user=user if user.is_authenticated else None,
                    email=(user.email or '') if user.is_authenticated else '',
                    answers=answers,
                    unique_value=unique_value,
                )
                for key, field_files in uploads.items():
                    for upload in field_files:
                        ResponseFile.objects.create(
                            response=response,
                            field_key=key,
                            file=upload,
                            original_name=upload.name[:255],
                        )
        except IntegrityError:
            return get_already_exists_response(message='ALREADY_SUBMITTED')

        return get_successful_creation_response(
            data={'id': response.id}, message='Response has been saved.'
        )
