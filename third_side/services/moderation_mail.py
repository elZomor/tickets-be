"""Moderation mail: a warning to the author of reported content, and a short
thank-you to each reporter once their report is resolved.

Text is trilingual (ar / en / ro) and follows the recipient's `language`. The
warning body is a template the moderator may edit before it is sent.
"""

import logging
from html import escape

from django.conf import settings

from third_side.services.mail import send_email

logger = logging.getLogger(__name__)

COPY = {
    'ar': {
        'dir': 'rtl',
        'warn_subject': 'تنبيه بخصوص محتوى على الضلع الثالث',
        'warn_body': 'أهلاً {name}،\n\nراجع فريق الإشراف في الضلع الثالث {target} الذي نشرته، وتبيّن أنه لا يتوافق مع إرشادات النشر لدينا.\n\nنرجو الالتزام بالإرشادات في ما تنشره لاحقاً. تكرار المخالفة قد يؤدي إلى إيقاف الحساب.\n\nإن رأيت أن هذا القرار غير صحيح فيمكنك الرد على هذه الرسالة.',
        'target_comment': 'تعليقك',
        'target_article': 'مقالك',
        'thanks_subject': 'شكراً على بلاغك',
        'thanks_body': 'أهلاً {name}،\n\nشكراً لك على الإبلاغ. راجع فريق الإشراف بلاغك واتخذ الإجراء المناسب. بلاغات القرّاء تساعدنا في الحفاظ على مكان آمن للنقاش.',
    },
    'en': {
        'dir': 'ltr',
        'warn_subject': 'A notice about your content on Third Side',
        'warn_body': 'Hi {name},\n\nOur moderation team reviewed {target} you posted on Third Side and found that it does not follow our publishing guidelines.\n\nPlease follow the guidelines in what you post from now on. Repeated violations may lead to your account being suspended.\n\nIf you believe this decision is wrong, you can reply to this message.',
        'target_comment': 'your comment',
        'target_article': 'your article',
        'thanks_subject': 'Thank you for your report',
        'thanks_body': 'Hi {name},\n\nThank you for reporting. Our moderation team has reviewed your report and taken the appropriate action. Reports from readers help us keep a safe place for discussion.',
    },
    'ro': {
        'dir': 'ltr',
        'warn_subject': 'O notificare despre conținutul tău de pe Third Side',
        'warn_body': 'Salut {name},\n\nEchipa noastră de moderare a verificat {target} publicat de tine pe Third Side și a constatat că nu respectă regulile de publicare.\n\nTe rugăm să respecți regulile în ce publici de acum încolo. Încălcările repetate pot duce la suspendarea contului.\n\nDacă crezi că decizia este greșită, poți răspunde la acest mesaj.',
        'target_comment': 'comentariul tău',
        'target_article': 'articolul tău',
        'thanks_subject': 'Îți mulțumim pentru raportare',
        'thanks_body': 'Salut {name},\n\nÎți mulțumim pentru raportare. Echipa de moderare ți-a verificat raportarea și a luat măsurile potrivite. Raportările cititorilor ne ajută să păstrăm un loc sigur pentru discuții.',
    },
}


def warning_template(user, target_kind):
    """Subject + body the moderator starts from, in the author's language."""
    c = COPY[user.language]
    target = c['target_comment'] if target_kind == 'comment' else c['target_article']
    return {
        'language': user.language,
        'subject': c['warn_subject'],
        'body': c['warn_body'].format(name=user.display_name, target=target),
    }


def _html(text):
    paragraphs = [p for p in text.strip().split('\n\n') if p.strip()]
    return ''.join(
        f'<p>{escape(p.strip()).replace(chr(10), "<br>")}</p>' for p in paragraphs
    )


def _send(user, subject, text, direction):
    if not settings.THIRD_SIDE_SEND_EMAIL:
        return False
    try:
        send_email(user.email, subject, _html(text), direction)
    except Exception:  # noqa: BLE001 - mail failure must never undo a decision
        logger.exception('Moderation email failed (%s)', subject)
        return False
    return True


def send_warning(user, subject, body):
    return _send(user, subject, body, COPY[user.language]['dir'])


def send_reporter_thanks(reporter):
    c = COPY[reporter.language]
    return _send(
        reporter,
        c['thanks_subject'],
        c['thanks_body'].format(name=reporter.display_name),
        c['dir'],
    )
