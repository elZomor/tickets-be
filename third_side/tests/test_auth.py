from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase

from third_side.models import ThirdSideUser

User = ThirdSideUser
# Migration 0014 publishes terms v1.0, so every signup must accept it.
SIGNUP = {
    'name': 'Sara Ali',
    'email': 'Sara@Example.com',
    'password': 'S3cure-pass!',
    'accepted_terms_version': '1.0',
}


class AuthFlowTests(APITestCase):
    def test_signup_returns_token_pair_and_profile(self):
        response = self.client.post('/third_side/auth/signup', SIGNUP, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.data), {'access', 'refresh'})
        me = self.client.get(
            '/third_side/profile/me',
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['name'], 'Sara Ali')
        self.assertEqual(me.data['email'], 'sara@example.com')
        self.assertEqual(me.data['role'], 'READER')

    def test_signup_duplicate_email_is_field_error(self):
        self.client.post('/third_side/auth/signup', SIGNUP, format='json')
        response = self.client.post(
            '/third_side/auth/signup',
            {**SIGNUP, 'email': 'sara@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_signup_short_password_rejected(self):
        response = self.client.post(
            '/third_side/auth/signup', {**SIGNUP, 'password': 'short'}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_login_with_email_via_token_endpoint(self):
        self.client.post('/third_side/auth/signup', SIGNUP, format='json')
        response = self.client.post(
            '/third_side/auth/login',
            {'email': 'Sara@example.com', 'password': SIGNUP['password']},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_login_wrong_password_is_400(self):
        self.client.post('/third_side/auth/signup', SIGNUP, format='json')
        response = self.client.post(
            '/third_side/auth/login',
            {'email': 'sara@example.com', 'password': 'nope-nope-nope'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_forgot_password_never_reveals_account(self):
        for email in ('sara@example.com', 'ghost@example.com'):
            response = self.client.post(
                '/third_side/auth/forgot-password', {'email': email}, format='json'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {'ok': True})

    def test_reset_password_with_valid_token(self):
        user = User.objects.create_user('u1@example.com', 'Old-pass-123')
        payload = {
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
            'password': 'New-pass-456!',
        }
        response = self.client.post(
            '/third_side/auth/reset-password', payload, format='json'
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password('New-pass-456!'))
        again = self.client.post(
            '/third_side/auth/reset-password', payload, format='json'
        )
        self.assertEqual(again.status_code, 400)

    def test_reset_password_bad_token(self):
        user = User.objects.create_user('u2@example.com', 'Old-pass-123')
        response = self.client.post(
            '/third_side/auth/reset-password',
            {
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': 'bad',
                'password': 'New-pass-456!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_forgot_password_link_uses_localized_fe_segment(self):
        from unittest import mock

        from django.test import override_settings

        User.objects.create_user('u3@example.com', 'Old-pass-123')
        with (
            override_settings(
                THIRD_SIDE_FE_URL='https://fe.test', THIRD_SIDE_SEND_EMAIL=True
            ),
            mock.patch('third_side.views.AuthViews.send_email') as send,
        ):
            for lang, segment in (
                ('en', 'reset-password'),
                ('ro', 'parola-noua'),
                ('ar', '%D9%83%D9%84%D9%85%D8%A9'),
            ):
                self.client.post(
                    '/third_side/auth/forgot-password',
                    {'email': 'u3@example.com', 'lang': lang},
                    format='json',
                )
                body = send.call_args.kwargs['body']
                self.assertIn(f'https://fe.test/{lang}/{segment}', body)
                self.assertIn('?uid=', body)

    def test_refresh_rotates_and_rejects_garbage(self):
        tokens = self.client.post('/third_side/auth/signup', SIGNUP, format='json').data
        response = self.client.post(
            '/third_side/auth/refresh', {'refresh': tokens['refresh']}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {'access', 'refresh'})
        bad = self.client.post(
            '/third_side/auth/refresh', {'refresh': 'garbage'}, format='json'
        )
        self.assertEqual(bad.status_code, 401)
        # An access token is not a refresh token.
        wrong = self.client.post(
            '/third_side/auth/refresh', {'refresh': tokens['access']}, format='json'
        )
        self.assertEqual(wrong.status_code, 401)

    def test_inactive_user_cannot_log_in(self):
        ThirdSideUser.objects.create_user(
            'off@example.com', 'Pass-1234-xyz', is_active=False
        )
        response = self.client.post(
            '/third_side/auth/login',
            {'email': 'off@example.com', 'password': 'Pass-1234-xyz'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_realms_are_isolated(self):
        """A shared django-User token must not open Third Side, nor the reverse."""
        from django.contrib.auth.models import User as DjangoUser
        from rest_framework_simplejwt.tokens import RefreshToken

        django_user = DjangoUser.objects.create_user(
            'legacy', 'l@example.com', 'pw-12345678'
        )
        legacy = str(RefreshToken.for_user(django_user).access_token)
        response = self.client.get(
            '/third_side/profile/me', HTTP_AUTHORIZATION=f'Bearer {legacy}'
        )
        self.assertEqual(response.status_code, 401)

        ours = self.client.post('/third_side/auth/signup', SIGNUP, format='json').data[
            'access'
        ]
        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken

        request = APIRequestFactory().get('/', HTTP_AUTHORIZATION=f'Bearer {ours}')
        with self.assertRaises(InvalidToken):
            JWTAuthentication().authenticate(request)

    def test_signup_name_is_kept_and_email_lowercased(self):
        self.client.post('/third_side/auth/signup', SIGNUP, format='json')
        user = ThirdSideUser.objects.get()
        self.assertEqual((user.name, user.email), ('Sara Ali', 'sara@example.com'))
