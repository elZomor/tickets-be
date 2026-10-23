"""Outgoing Third Side mail through Brevo's HTTPS API.

The API, never SMTP: the host (Railway Hobby) blocks outbound SMTP ports.
Senders must be on THIRD_SIDE_MAIL_DOMAIN, which is authenticated in Brevo
(DKIM + DMARC), so any address on it may send.
"""

from html import escape

import requests
from django.conf import settings

BREVO_SEND_URL = 'https://api.brevo.com/v3/smtp/email'
TIMEOUT = 15


class MailError(Exception):
    pass


def is_on_mail_domain(email):
    return email.strip().lower().endswith('@' + settings.THIRD_SIDE_MAIL_DOMAIN)


def send(sender_email, sender_name, to, subject, html, cc=(), reply_to=None):
    """Send one message; returns Brevo's message id. Raises MailError."""
    if not settings.BREVO_API_KEY:
        raise MailError('BREVO_API_KEY is not set')
    payload = {
        'sender': {'email': sender_email, 'name': sender_name},
        'to': [{'email': address} for address in to],
        'subject': subject,
        'htmlContent': html,
        'replyTo': {'email': reply_to or sender_email, 'name': sender_name},
    }
    if cc:
        payload['cc'] = [{'email': address} for address in cc]
    try:
        response = requests.post(
            BREVO_SEND_URL,
            json=payload,
            headers={'api-key': settings.BREVO_API_KEY, 'accept': 'application/json'},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise MailError(f'Brevo unreachable: {exc}') from exc
    if response.status_code >= 300:
        try:
            message = response.json().get('message') or response.text
        except ValueError:
            message = response.text
        raise MailError(f'Brevo {response.status_code}: {message}')
    return response.json().get('messageId', '')


def send_email(to_email, subject, body):
    """System mail (password reset) from THIRD_SIDE_SYSTEM_SENDER."""
    return send(
        settings.THIRD_SIDE_SYSTEM_SENDER,
        'Third Side',
        [to_email],
        subject,
        render_email(body, 'ltr'),
    )


def render_email(body_html, direction='rtl'):
    """Wrap an editor-made body in a table layout mail clients agree on.

    The body arrives with inline styles already (the admin converts the
    editor's nodes); only the frame lives here.
    """
    align = 'right' if direction == 'rtl' else 'left'
    site = escape(settings.THIRD_SIDE_FE_URL)
    return f'''<!doctype html>
<html dir="{direction}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#f4f1ec;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1ec;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:6px;">
<tr><td dir="{direction}" style="padding:32px 28px;font-family:Tahoma,Arial,sans-serif;font-size:16px;line-height:1.7;color:#1f1f1f;text-align:{align};">
{body_html}
</td></tr>
<tr><td dir="{direction}" style="padding:16px 28px;border-top:1px solid #eee;font-family:Tahoma,Arial,sans-serif;font-size:12px;color:#888;text-align:{align};">
<a href="{site}" style="color:#888;">الضلع الثالث · Third Side</a>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>'''
