"""Validate a submission against a form's configured fields.

Error codes match the ones the festival application already uses (``required``,
``ARABIC_ONLY``, ``INVALID_MOBILE``, ``INVALID_FILE_TYPE``, ``FILE_TOO_LARGE``) so
the frontend can translate them the same way.
"""

import os
import re
from datetime import date

from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from dynamic_forms.models import FieldPreset, FieldType
from utils.validators import is_arabic_text, normalize_digits, normalize_egyptian_mobile

TRUE_VALUES = {'true', '1', 'on', 'yes'}
NUMBER_RE = re.compile(r'^-?\d+(?:\.\d+)?$')


def _text(data, key):
    value = data.get(key, '')
    return value.strip() if isinstance(value, str) else ''


def _list(data, key):
    if hasattr(data, 'getlist'):
        values = data.getlist(key)
    else:
        raw = data.get(key, [])
        values = raw if isinstance(raw, list) else [raw]
    return [v.strip() for v in values if isinstance(v, str) and v.strip()]


def _validate_text(field, value):
    """Return (cleaned value, error code or None) for text-like fields."""
    if field.type == FieldType.EMAIL:
        try:
            validate_email(value)
        except ValidationError:
            return value, 'INVALID_EMAIL'
        value = value.lower()
    elif field.type == FieldType.NUMBER:
        value = normalize_digits(value).replace(',', '.')
        if not NUMBER_RE.match(value):
            return value, 'INVALID_NUMBER'
    elif field.type == FieldType.DATE:
        try:
            date.fromisoformat(value)
        except ValueError:
            return value, 'INVALID_DATE'
    elif field.type == FieldType.PHONE:
        value = re.sub(r'\s+', '', normalize_digits(value))

    if field.preset == FieldPreset.EGYPT_MOBILE:
        mobile = normalize_egyptian_mobile(value)
        if not mobile:
            return value, 'INVALID_MOBILE'
        value = mobile
    elif field.preset == FieldPreset.ARABIC_ONLY and not is_arabic_text(value):
        return value, 'ARABIC_ONLY'

    if field.min_length is not None and len(value) < field.min_length:
        return value, 'TOO_SHORT'
    if field.max_length is not None and len(value) > field.max_length:
        return value, 'TOO_LONG'
    if field.pattern and not re.fullmatch(field.pattern, value):
        return value, 'INVALID_PATTERN'
    return value, None


def _validate_files(field, uploads):
    if len(uploads) > field.max_files:
        return 'TOO_MANY_FILES'
    extensions = field.normalized_extensions
    for upload in uploads:
        ext = os.path.splitext(upload.name)[1].lower()
        if extensions and ext not in extensions:
            return 'INVALID_FILE_TYPE'
        if upload.size > field.max_file_mb * 1024 * 1024:
            return 'FILE_TOO_LARGE'
    return None


def validate_answers(fields, data, files):
    """
    Return ``(answers, uploads, errors)``.

    ``answers`` maps field key to the cleaned value (files excluded), ``uploads``
    maps file field keys to their uploaded files and ``errors`` maps field keys to
    a list holding one error code (the DRF shape the frontend already parses).
    """
    answers, uploads, errors = {}, {}, {}

    for field in fields:
        key = field.key
        error = None

        if field.type == FieldType.FILE:
            field_files = files.getlist(key) if hasattr(files, 'getlist') else []
            if not field_files:
                error = 'required' if field.required else None
            else:
                error = _validate_files(field, field_files)
                uploads[key] = field_files

        elif field.type == FieldType.CONSENT:
            accepted = _text(data, key).lower() in TRUE_VALUES
            if field.required and not accepted:
                error = 'required'
            answers[key] = accepted

        elif field.type == FieldType.CHECKBOXES:
            values = _list(data, key)
            if not values:
                error = 'required' if field.required else None
            elif any(v not in field.options for v in values):
                error = 'INVALID_OPTION'
            # Keep the configured order, drop duplicates.
            answers[key] = [o for o in field.options if o in values]

        elif field.type in (FieldType.SELECT, FieldType.RADIO):
            value = _text(data, key)
            if not value:
                error = 'required' if field.required else None
            elif value not in field.options:
                error = 'INVALID_OPTION'
            answers[key] = value

        else:
            value = _text(data, key)
            if not value:
                error = 'required' if field.required else None
            else:
                value, error = _validate_text(field, value)
            answers[key] = value

        if error:
            errors[key] = [error]

    return answers, uploads, errors
