import os
import re

from django.core.exceptions import ValidationError

ARABIC_LETTER_RE = re.compile(r'[\u0621-\u064A\u066E-\u06D3\u06FA-\u06FC\u0750-\u077F]')
LATIN_LETTER_RE = re.compile(r'[A-Za-z]')
ALLOWED_ARABIC_TEXT_RE = re.compile(
    r'^[\u0600-\u06FF\u0750-\u077F\s0-9.,:;!?()\[\]"\'\-_/«»…–—%&+#*]+$'
)

ARABIC_INDIC_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')
EGYPTIAN_MOBILE_RE = re.compile(r'^(?:\+20|0020|20|0)?(1[0125]\d{8})$')


def is_arabic_text(value):
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value:
        return False
    if LATIN_LETTER_RE.search(value):
        return False
    if not ARABIC_LETTER_RE.search(value):
        return False
    return bool(ALLOWED_ARABIC_TEXT_RE.match(value))


def validate_arabic_text(value):
    if not is_arabic_text(value):
        raise ValidationError('ARABIC_ONLY', code='ARABIC_ONLY')


def normalize_digits(value):
    return (value or '').translate(ARABIC_INDIC_DIGITS)


def normalize_egyptian_mobile(value):
    """Return the mobile as 01XXXXXXXXX, or None when it is not a valid Egyptian mobile."""
    cleaned = re.sub(r'[\s\-()]', '', normalize_digits(value))
    match = EGYPTIAN_MOBILE_RE.match(cleaned)
    if not match:
        return None
    return f'0{match.group(1)}'


INTERNATIONAL_PHONE_RE = re.compile(r'^(?:\+|00)([1-9]\d{7,14})$')


def normalize_whatsapp(value):
    """
    Egyptian mobiles (local or +20) become 01XXXXXXXXX; any other country must be in
    international format (+ or 00 then 8-15 digits) and becomes +<digits>.
    Return None when invalid.
    """
    egyptian = normalize_egyptian_mobile(value)
    if egyptian:
        return egyptian
    cleaned = re.sub(r'[\s\-()]', '', normalize_digits(value))
    match = INTERNATIONAL_PHONE_RE.match(cleaned)
    if not match:
        return None
    return f'+{match.group(1)}'


def validate_upload(upload, allowed_extensions, max_size_mb):
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError('INVALID_FILE_TYPE', code='INVALID_FILE_TYPE')
    if upload.size > max_size_mb * 1024 * 1024:
        raise ValidationError('FILE_TOO_LARGE', code='FILE_TOO_LARGE')
