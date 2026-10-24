"""Account emails: confirm-your-address and welcome, in ar / en / ro.

The confirmation link carries a signed token (uid + the email it vouches for),
valid for TOKEN_MAX_AGE. It dies if the address changes, and unlike Django's
password-reset token it does not depend on `last_login`.
"""

import logging
from html import escape
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from third_side.services.mail import send_email

logger = logging.getLogger(__name__)

TOKEN_SALT = 'third-side.verify-email'
TOKEN_MAX_AGE = 3 * 24 * 60 * 60

# The FE serves these pages at localized URL segments (accountPaths.ts).
VERIFY_SEGMENTS = {'ar': 'تأكيد-البريد', 'en': 'verify-email', 'ro': 'confirmare-email'}
PROFILE_SEGMENTS = {'ar': 'ملفي-الشخصي', 'en': 'profile', 'ro': 'profil'}
SUBMIT_SEGMENTS = {'ar': 'إرسال-مقال', 'en': 'submit-article', 'ro': 'trimite-articol'}

COPY = {
    'ar': {
        'dir': 'rtl',
        'verify_subject': 'أهلاً بك في الضلع الثالث — أكّد بريدك الإلكتروني',
        'verify_hello': 'أهلاً {name}،',
        'verify_intro': 'سعداء بانضمامك إلى الضلع الثالث. بقيت خطوة واحدة صغيرة: أكّد بريدك الإلكتروني لنفتح لك كل شيء — إرسال مقالاتك، وإضافة صورتك ونبذة عنك.',
        'verify_button': 'تأكيد البريد الإلكتروني',
        'verify_fallback': 'إن لم يعمل الزر، انسخ هذا الرابط في المتصفح:',
        'verify_note': 'الرابط صالح لمدة ٣ أيام. إن لم تنشئ حساباً عندنا فتجاهل هذه الرسالة، ولن يحدث شيء.',
        'welcome_subject': 'تم تأكيد بريدك — مرحباً بك في الضلع الثالث',
        'welcome_hello': 'مرحباً {name}،',
        'welcome_intro': 'شكراً لتأكيد بريدك، وأهلاً بك بين قرّائنا وكتّابنا. صار بإمكانك الآن:',
        'welcome_items': ['إرسال مقالك ليراجعه فريق التحرير', 'إضافة صورتك الشخصية ونبذة قصيرة عنك'],
        'welcome_profile': 'أكمل ملفك الشخصي',
        'welcome_submit': 'أرسل مقالاً',
        'welcome_close': 'نكتب عن الفن من زاوية ثالثة — ويسعدنا أن تكون جزءاً منها.',
    },
    'en': {
        'dir': 'ltr',
        'verify_subject': 'Welcome to Third Side — please confirm your email',
        'verify_hello': 'Hi {name},',
        'verify_intro': "We're glad you joined Third Side. One small step left: confirm your email address so we can unlock everything — submitting your articles, adding your photo and a short bio.",
        'verify_button': 'Confirm my email',
        'verify_fallback': "If the button doesn't work, paste this link into your browser:",
        'verify_note': "The link is valid for 3 days. If you didn't create an account with us, just ignore this message and nothing will happen.",
        'welcome_subject': "You're confirmed — welcome to Third Side",
        'welcome_hello': 'Hi {name},',
        'welcome_intro': "Thanks for confirming your email, and welcome among our readers and writers. You can now:",
        'welcome_items': ['Submit an article for our editors to review', 'Add your photo and a short bio'],
        'welcome_profile': 'Complete your profile',
        'welcome_submit': 'Submit an article',
        'welcome_close': "We write about the arts from a third angle — we're happy to have you in it.",
    },
    'ro': {
        'dir': 'ltr',
        'verify_subject': 'Bun venit la Third Side — confirmă adresa de email',
        'verify_hello': 'Salut {name},',
        'verify_intro': 'Ne bucurăm că te-ai alăturat Third Side. Mai e un pas mic: confirmă adresa de email ca să deblocăm totul — trimiterea articolelor, poza ta și o scurtă prezentare.',
        'verify_button': 'Confirmă emailul',
        'verify_fallback': 'Dacă butonul nu merge, copiază acest link în browser:',
        'verify_note': 'Linkul este valabil 3 zile. Dacă nu ai creat un cont la noi, ignoră acest mesaj și nu se întâmplă nimic.',
        'welcome_subject': 'Email confirmat — bun venit la Third Side',
        'welcome_hello': 'Salut {name},',
        'welcome_intro': 'Mulțumim că ți-ai confirmat emailul și bine ai venit printre cititorii și autorii noștri. Acum poți:',
        'welcome_items': ['Să trimiți un articol pentru a fi revizuit de redacție', 'Să adaugi poza ta și o scurtă prezentare'],
        'welcome_profile': 'Completează-ți profilul',
        'welcome_submit': 'Trimite un articol',
        'welcome_close': 'Scriem despre artă dintr-un al treilea unghi — ne bucurăm să fii parte din el.',
    },
}


def make_token(user):
    return signing.dumps({'u': user.pk, 'e': user.email}, salt=TOKEN_SALT)


def read_token(uid, token):
    """The user a valid token vouches for, or None (bad, expired, email changed)."""
    from third_side.models import ThirdSideUser

    try:
        data = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        if str(data['u']) != force_str(urlsafe_base64_decode(uid)):
            return None
        user = ThirdSideUser.objects.get(pk=data['u'], is_active=True)
    except (
        signing.BadSignature,
        KeyError,
        ThirdSideUser.DoesNotExist,
        ValueError,
        TypeError,
        OverflowError,
    ):
        return None
    return user if user.email == data['e'] else None


def _page_url(segments, lang, query=''):
    return f'{settings.THIRD_SIDE_FE_URL}/{lang}/{quote(segments[lang])}{query}'


def _button(url, label):
    return (
        f'<p style="margin:24px 0;"><a href="{escape(url)}" style="display:inline-block;'
        'background:#9a3412;color:#ffffff;text-decoration:none;padding:12px 28px;'
        f'border-radius:6px;font-weight:bold;">{escape(label)}</a></p>'
    )


def verification_link(user):
    lang = user.language
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return _page_url(VERIFY_SEGMENTS, lang, f'?uid={uid}&token={quote(make_token(user))}')


def _safe_send(user, subject, body, direction):
    if not settings.THIRD_SIDE_SEND_EMAIL:
        return False
    try:
        send_email(user.email, subject, body, direction)
    except Exception:  # noqa: BLE001 - mail failure must never break the request
        logger.exception('Account email failed (%s)', subject)
        return False
    return True


def send_verification_email(user):
    c = COPY[user.language]
    link = verification_link(user)
    body = (
        f'<p>{escape(c["verify_hello"].format(name=user.display_name))}</p>'
        f'<p>{escape(c["verify_intro"])}</p>'
        f'{_button(link, c["verify_button"])}'
        f'<p style="font-size:13px;color:#666;">{escape(c["verify_fallback"])}<br>'
        f'<a href="{escape(link)}" style="color:#666;word-break:break-all;" dir="ltr">{escape(link)}</a></p>'
        f'<p style="font-size:13px;color:#666;">{escape(c["verify_note"])}</p>'
    )
    return _safe_send(user, c['verify_subject'], body, c['dir'])


def send_welcome_email(user):
    c = COPY[user.language]
    lang = user.language
    items = ''.join(f'<li>{escape(item)}</li>' for item in c['welcome_items'])
    body = (
        f'<p>{escape(c["welcome_hello"].format(name=user.display_name))}</p>'
        f'<p>{escape(c["welcome_intro"])}</p><ul>{items}</ul>'
        f'{_button(_page_url(PROFILE_SEGMENTS, lang), c["welcome_profile"])}'
        f'<p><a href="{escape(_page_url(SUBMIT_SEGMENTS, lang))}" style="color:#9a3412;">'
        f'{escape(c["welcome_submit"])}</a></p>'
        f'<p>{escape(c["welcome_close"])}</p>'
    )
    return _safe_send(user, c['welcome_subject'], body, c['dir'])


def mark_verified(user):
    """Verify the address; the welcome mail goes out once, on the first time."""
    if user.email_verified:
        return False
    user.email_verified = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=['email_verified', 'email_verified_at'])
    send_welcome_email(user)
    return True
