from datetime import date, timedelta
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase

from third_side.models import ThirdSideUser
from third_side.services import account_mail

User = ThirdSideUser
SIGNUP = {
    'name': 'Sara Ali',
    'email': 'sara@example.com',
    'password': 'S3cure-pass!',
    'accepted_terms_version': '1.0',
}
MAIL = 'third_side.services.account_mail.send_email'


def uid_of(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def sign_up(client, **extra):
    response = client.post(
        '/third_side/auth/signup', {**SIGNUP, **extra}, format='json'
    )
    assert response.status_code == 201, response.data
    return response.data['access']


@override_settings(THIRD_SIDE_SEND_EMAIL=True, THIRD_SIDE_FE_URL='https://fe.test')
class VerificationFlowTests(APITestCase):
    def setUp(self):
        cache.clear()  # the auth throttle is shared by the whole suite

    def test_signup_creates_unverified_user_and_sends_localized_mail(self):
        with mock.patch(MAIL) as send, self.captureOnCommitCallbacks(execute=True):
            access = sign_up(self.client, lang='en')
        user = User.objects.get(email='sara@example.com')
        self.assertFalse(user.email_verified)
        self.assertEqual(user.language, 'en')
        send.assert_called_once()
        to, subject, body, direction = send.call_args.args
        self.assertEqual(to, 'sara@example.com')
        self.assertIn('confirm', subject.lower())
        self.assertIn('https://fe.test/en/verify-email?uid=', body)
        self.assertEqual(direction, 'ltr')
        me = self.client.get(
            '/third_side/profile/me', HTTP_AUTHORIZATION=f'Bearer {access}'
        )
        self.assertFalse(me.data['email_verified'])

    def test_arabic_mail_is_rtl(self):
        with mock.patch(MAIL) as send, self.captureOnCommitCallbacks(execute=True):
            sign_up(self.client)
        self.assertEqual(send.call_args.args[3], 'rtl')

    def test_verify_marks_user_and_sends_welcome_once(self):
        user = User.objects.create_user('v@example.com', 'x', language='ro')
        payload = {'uid': uid_of(user), 'token': account_mail.make_token(user)}
        with mock.patch(MAIL) as send:
            first = self.client.post(
                '/third_side/auth/verify-email', payload, format='json'
            )
            second = self.client.post(
                '/third_side/auth/verify-email', payload, format='json'
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIsNotNone(user.email_verified_at)
        send.assert_called_once()  # the welcome mail
        self.assertIn('bun venit', send.call_args.args[1].lower())

    def test_tampered_expired_and_wrong_uid_tokens_are_refused(self):
        user = User.objects.create_user('v@example.com', 'x')
        other = User.objects.create_user('o@example.com', 'x')
        good = account_mail.make_token(user)
        with mock.patch(
            'django.core.signing.time.time',
            return_value=__import__('time').time() + account_mail.TOKEN_MAX_AGE + 60,
        ):
            expired = self.client.post(
                '/third_side/auth/verify-email',
                {'uid': uid_of(user), 'token': good},
                format='json',
            )
        cases = {
            'tampered': {'uid': uid_of(user), 'token': good[:-2] + 'xx'},
            'wrong uid': {'uid': uid_of(other), 'token': good},
            'garbage uid': {'uid': '!!', 'token': good},
        }
        self.assertEqual(expired.status_code, 400)
        for name, payload in cases.items():
            response = self.client.post(
                '/third_side/auth/verify-email', payload, format='json'
            )
            self.assertEqual(response.status_code, 400, name)
        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    def test_token_dies_when_email_changes(self):
        user = User.objects.create_user('v@example.com', 'x')
        token = account_mail.make_token(user)
        user.email = 'new@example.com'
        user.save()
        response = self.client.post(
            '/third_side/auth/verify-email',
            {'uid': uid_of(user), 'token': token},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_resend_sends_for_unverified_and_not_for_verified(self):
        access = sign_up(self.client)
        auth = {'HTTP_AUTHORIZATION': f'Bearer {access}'}
        with mock.patch(MAIL) as send:
            response = self.client.post(
                '/third_side/auth/resend-verification', {}, format='json', **auth
            )
        self.assertEqual(response.status_code, 200)
        send.assert_called_once()
        User.objects.update(email_verified=True)
        with mock.patch(MAIL) as send:
            self.client.post(
                '/third_side/auth/resend-verification', {}, format='json', **auth
            )
        send.assert_not_called()

    def test_resend_needs_sign_in(self):
        response = self.client.post(
            '/third_side/auth/resend-verification', {}, format='json'
        )
        self.assertEqual(response.status_code, 401)

    def test_mail_failure_does_not_break_signup(self):
        with mock.patch(MAIL, side_effect=RuntimeError('boom')), (
            self.captureOnCommitCallbacks(execute=True)
        ):
            sign_up(self.client)


class GateAndProfileTests(APITestCase):
    def setUp(self):
        cache.clear()

    def auth(self, verified):
        access = sign_up(self.client)
        if verified:
            User.objects.update(email_verified=True)
        return {'HTTP_AUTHORIZATION': f'Bearer {access}'}

    def test_unverified_cannot_submit_or_upload_or_change_avatar(self):
        auth = self.auth(verified=False)
        for method, url in (
            ('post', '/third_side/submissions'),
            ('post', '/third_side/media'),
            ('post', '/third_side/profile/me/avatar'),
            ('delete', '/third_side/profile/me/avatar'),
        ):
            response = getattr(self.client, method)(url, {}, **auth)
            self.assertEqual(response.status_code, 403, url)
            self.assertEqual(response.data['code'], 'email_not_verified')

    def test_unverified_can_still_list_own_submissions(self):
        auth = self.auth(verified=False)
        response = self.client.get('/third_side/submissions/mine', **auth)
        self.assertEqual(response.status_code, 200)

    def test_verified_passes_the_gate(self):
        auth = self.auth(verified=True)
        response = self.client.post('/third_side/submissions', {}, format='json', **auth)
        self.assertEqual(response.status_code, 400)  # validation, not 403

    def test_staff_are_exempt(self):
        user = User.objects.create_user('st@example.com', 'x', is_superuser=True)
        self.assertTrue(user.can_contribute)

    def test_existing_fields_editable_unverified_but_bio_is_not(self):
        auth = self.auth(verified=False)
        ok = self.client.patch(
            '/third_side/profile/me',
            {
                'name': 'Sara A.',
                'gender': 'female',
                'governorate': 'cairo',
                'date_of_birth': '1995-04-02',
                'newsletter_opt_in': True,
            },
            format='json',
            **auth,
        )
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(ok.data['governorate'], 'cairo')
        self.assertEqual(ok.data['name'], 'Sara A.')
        self.assertTrue(ok.data['newsletter_opt_in'])
        bio = self.client.patch(
            '/third_side/profile/me', {'bio': 'Hi'}, format='json', **auth
        )
        self.assertEqual(bio.status_code, 403)
        self.assertEqual(bio.data['code'], 'email_not_verified')

    def test_verified_can_write_bio(self):
        auth = self.auth(verified=True)
        response = self.client.patch(
            '/third_side/profile/me', {'bio': '  Theatre nerd  '}, format='json', **auth
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['bio'], 'Theatre nerd')

    def test_profile_validation(self):
        auth = self.auth(verified=True)
        today = timezone.localdate()
        bad = {
            'date_of_birth': (today - timedelta(days=365 * 5)).isoformat(),
            'governorate': 'atlantis',
            'gender': 'x',
            'bio': 'a' * 501,
        }
        for field, value in bad.items():
            response = self.client.patch(
                '/third_side/profile/me', {field: value}, format='json', **auth
            )
            self.assertEqual(response.status_code, 400, field)
        future = self.client.patch(
            '/third_side/profile/me',
            {'date_of_birth': (today + timedelta(days=2)).isoformat()},
            format='json',
            **auth,
        )
        self.assertEqual(future.status_code, 400)
        cleared = self.client.patch(
            '/third_side/profile/me', {'date_of_birth': None}, format='json', **auth
        )
        self.assertEqual(cleared.status_code, 200)

    def test_profile_is_read_only_for_email_and_verified_flag(self):
        auth = self.auth(verified=False)
        self.client.patch(
            '/third_side/profile/me',
            {'email': 'x@y.com', 'email_verified': True},
            format='json',
            **auth,
        )
        user = User.objects.get()
        self.assertEqual(user.email, 'sara@example.com')
        self.assertFalse(user.email_verified)
