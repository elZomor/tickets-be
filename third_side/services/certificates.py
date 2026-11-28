"""Certificates: building the template variables, rendering, issuing.

A template is HTML in Django template syntax (autoescaped). Variables:

    participant_name, certificate_title, certificate_title_latin,
    completed_verb, kind_label, program_title_html, details (list),
    partner_text, partner_logo_url, issued_date, signatory_title,
    signatory_name, signature_url, code, verify_url, qr_svg, site_url

`program_title_html` is the title, escaped, with *word* turned into
<span class="accent">word</span>. Everything is frozen into Certificate.context
when issued, except code/verify_url/qr_svg/site_url, added on render.
"""

import io
import re
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.template import Context, Template
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe

from third_side.models import Certificate, CertificateTemplate, LabRegistration
from third_side.models.LabRegistration import RegistrationStatus
from third_side.services.media_urls import to_url

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / 'templates' / 'third_side'
DEFAULT_FILES = {
    'ar': TEMPLATE_DIR / 'certificates' / 'attendance_ar.html',
    'en': TEMPLATE_DIR / 'certificates' / 'attendance_en.html',
}

DEFAULTS = {
    'ar': {
        'certificate_title': 'شهادة حضور',
        'certificate_title_latin': 'Certificate of Attendance',
        'signatory_title': 'مؤسس ورئيس التحرير',
    },
    'en': {
        'certificate_title': 'Certificate of Attendance',
        'certificate_title_latin': 'شهادة حضور',
        'signatory_title': 'Founder & Editor-in-Chief',
    },
}

KIND_LABEL = {
    'ar': {
        'workshop': 'الورشة',
        'seminar': 'الندوة',
        'masterclass': 'الماستر كلاس',
        'talk': 'اللقاء',
        'event': 'الفعالية',
        'other': 'البرنامج',
    },
    'en': {
        'workshop': 'the workshop',
        'seminar': 'the seminar',
        'masterclass': 'the masterclass',
        'talk': 'the talk',
        'event': 'the event',
        'other': 'the program',
    },
}

AR_MONTHS = [
    'يناير',
    'فبراير',
    'مارس',
    'أبريل',
    'مايو',
    'يونيو',
    'يوليو',
    'أغسطس',
    'سبتمبر',
    'أكتوبر',
    'نوفمبر',
    'ديسمبر',
]
EN_MONTHS = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
]
AR_DIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
_ACCENT = re.compile(r'\*([^*]+)\*')


def format_date(day, lang):
    if lang == 'ar':
        return f'{day.day} {AR_MONTHS[day.month - 1]} {day.year}'.translate(AR_DIGITS)
    return f'{day.day} {EN_MONTHS[day.month - 1]} {day.year}'


def title_html(text):
    """Escape, then mark *word* as the accent colour."""
    return _ACCENT.sub(r'<span class="accent">\1</span>', escape(text or ''))


def completed_verb(lang, gender):
    if lang == 'en':
        return 'has successfully attended'
    return 'أتمّت' if gender == 'female' else 'أتمّ'


def missing_english(program):
    """The English fields a program still lacks before English certificates."""
    missing = []
    if not program.cert_program_title_i18n.get('en') and not program.title_i18n.get(
        'en'
    ):
        missing.append('cert_program_title_i18n')
    if program.partner_name_i18n.get('ar') and not program.partner_name_i18n.get('en'):
        missing.append('partner_name_i18n')
    details = program.cert_details_i18n or {}
    if details.get('ar') and not details.get('en'):
        missing.append('cert_details_i18n')
    return missing


def program_context(program, lang, request=None):
    """Variables that come from the program, in `lang` (no fallback language:
    an English certificate must not show Arabic text)."""

    def pick(values, default=''):
        values = values if isinstance(values, dict) else {}
        return values.get(lang) or default

    defaults = DEFAULTS[lang]
    title = pick(program.cert_program_title_i18n) or pick(program.title_i18n)
    details = (program.cert_details_i18n or {}).get(lang) or []
    issued_on = program.cert_issued_on or program.ends_on
    return {
        'certificate_title': pick(
            program.cert_title_i18n, defaults['certificate_title']
        ),
        'certificate_title_latin': defaults['certificate_title_latin'],
        'kind_label': pick(
            program.cert_kind_label_i18n, KIND_LABEL[lang].get(program.kind, '')
        ),
        'program_title_html': title_html(title),
        'details': [str(item) for item in details if str(item).strip()],
        'partner_text': pick(program.partner_name_i18n),
        'partner_logo_url': to_url(program.partner_logo_url, request) or '',
        'issued_date': format_date(issued_on, lang),
        'signatory_title': defaults['signatory_title'],
        'signatory_name': '',
        'signature_url': '',
    }


def template_for(program, lang):
    chosen = program.cert_template_ar if lang == 'ar' else program.cert_template_en
    return chosen or ensure_default_template(lang)


def ensure_default_template(lang):
    """The default template of `lang`, created from the bundled file if none."""
    found = CertificateTemplate.objects.filter(language=lang, is_default=True).first()
    if found:
        return found
    found = CertificateTemplate.objects.filter(language=lang).first()
    if found:
        return found
    return CertificateTemplate.objects.create(
        name='Attendance' if lang == 'en' else 'حضور',
        language=lang,
        html=DEFAULT_FILES[lang].read_text(encoding='utf-8'),
        is_default=True,
    )


def verify_url(code, lang):
    from third_side.services.lab import certificate_paths

    return settings.THIRD_SIDE_FE_URL.rstrip('/') + certificate_paths(code)[lang]


def qr_svg(url):
    import qrcode
    import qrcode.image.svg

    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=0)
    buffer = io.BytesIO()
    image.save(buffer)
    svg = buffer.getvalue().decode('utf-8')
    return svg.split('?>', 1)[-1].strip()


def render(html, context, code, lang):
    """Render template `html` with a frozen `context` plus the live variables."""
    url = verify_url(code, lang) if code else ''
    data = dict(context)
    data['program_title_html'] = mark_safe(data.get('program_title_html', ''))
    data.update(
        code=code,
        verify_url=url,
        qr_svg=mark_safe(qr_svg(url)) if url else '',
        site_url=settings.THIRD_SIDE_FE_URL.rstrip('/'),
    )
    return Template(html).render(Context(data))


def render_certificate(certificate):
    template = certificate.template or ensure_default_template(certificate.language)
    return render(
        template.html, certificate.context, certificate.code, certificate.language
    )


def sample_context(lang):
    """Example variables for the template editor's preview."""
    if lang == 'en':
        return {
            'participant_name': 'Mohamed Ahmed Abdelrahman',
            'certificate_title': 'Certificate of Attendance',
            'certificate_title_latin': 'شهادة حضور',
            'completed_verb': completed_verb('en', ''),
            'kind_label': 'the intensive workshop',
            'program_title_html': title_html(
                '*Applied Criticism* in Theatre Festival Bulletins'
            ),
            'details': ['Introductory workshop', '3 days', '9 hours'],
            'partner_text': 'the Higher Institute of Dramatic Arts',
            'partner_logo_url': '',
            'issued_date': format_date(timezone.localdate(), 'en'),
            'signatory_title': DEFAULTS['en']['signatory_title'],
            'signatory_name': '',
            'signature_url': '',
        }
    return {
        'participant_name': 'محمد أحمد عبد الرحمن',
        'certificate_title': 'شهادة حضور',
        'certificate_title_latin': 'Certificate of Attendance',
        'completed_verb': completed_verb('ar', ''),
        'kind_label': 'الورشة المكثفة',
        'program_title_html': title_html(
            '*النقد التطبيقي* في نشرات المهرجانات المسرحية'
        ),
        'details': [
            'ورشة تمهيدية لنقاد نشرة مهرجان المسرح العربي',
            '٣ أيام',
            '٩ ساعات',
        ],
        'partner_text': 'المعهد العالي للفنون المسرحية',
        'partner_logo_url': '',
        'issued_date': format_date(timezone.localdate(), 'ar'),
        'signatory_title': DEFAULTS['ar']['signatory_title'],
        'signatory_name': '',
        'signature_url': '',
    }


def _issue(program, user, lang, name, registration=None, source=None, request=None):
    """Create one certificate; None when the user already has this one."""
    if Certificate.objects.filter(user=user, program=program, language=lang).exists():
        return None
    context = program_context(program, lang, request)
    context['participant_name'] = name
    context['completed_verb'] = completed_verb(lang, getattr(user, 'gender', ''))
    for _ in range(3):
        try:
            with transaction.atomic():
                return Certificate.objects.create(
                    user=user,
                    program=program,
                    registration=registration,
                    language=lang,
                    source=source,
                    participant_name=name,
                    template=template_for(program, lang),
                    context=context,
                )
        except IntegrityError:
            # A parallel issue won, or (rarely) the random code clashed: retry.
            if Certificate.objects.filter(
                user=user, program=program, language=lang
            ).exists():
                return None
    raise IntegrityError('Could not pick a free certificate code')


def issue_arabic(program, request=None, registration_ids=None):
    """AR certificates for every attended registration that has none yet.

    Returns the new certificates. `registration_ids` limits the batch.
    """
    registrations = LabRegistration.objects.filter(
        program=program, attended=True
    ).select_related('user')
    if registration_ids is not None:
        registrations = registrations.filter(pk__in=registration_ids)
    have = set(
        Certificate.objects.filter(program=program, language='ar').values_list(
            'user_id', flat=True
        )
    )
    issued = []
    for registration in registrations:
        if registration.user_id in have:
            continue
        if registration.status == RegistrationStatus.REJECTED:
            continue
        name = (registration.user.name or '').strip() or registration.user.email
        certificate = _issue(
            program, registration.user, 'ar', name, registration, request=request
        )
        if certificate:
            issued.append(certificate)
    return issued


class EnglishUnavailable(Exception):
    pass


def request_english(certificate, name_en, request=None):
    """Issue the English version of an Arabic certificate now, or hold the
    request until the program has English text. Returns the English
    certificate, or None when it waits."""
    if certificate.language != 'ar' or certificate.revoked:
        raise EnglishUnavailable('not_arabic')
    existing = certificate.translations.filter(language='en').first()
    if existing:
        return existing
    program = certificate.program
    if missing_english(program):
        certificate.english_name_requested = name_en
        certificate.save(update_fields=['english_name_requested'])
        return None
    english = _issue(
        program,
        certificate.user,
        'en',
        name_en,
        certificate.registration,
        source=certificate,
        request=request,
    )
    if certificate.english_name_requested:
        certificate.english_name_requested = ''
        certificate.save(update_fields=['english_name_requested'])
    return english


def issue_waiting_english(program):
    """English certificates held for this program, now that it has English."""
    if missing_english(program):
        return []
    issued = []
    waiting = Certificate.objects.filter(
        program=program, language='ar', revoked=False
    ).exclude(english_name_requested='')
    for certificate in waiting:
        english = request_english(certificate, certificate.english_name_requested)
        if english:
            issued.append(english)
    return issued
