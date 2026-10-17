from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase

User = get_user_model()
SIGNUP = {'name': 'Sara Ali', 'email': 'Sara@Example.com', 'password': 'S3cure-pass!'}


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
            '/token/',
            {'username': 'sara@example.com', 'password': SIGNUP['password']},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_login_wrong_password_is_400(self):
        self.client.post('/third_side/auth/signup', SIGNUP, format='json')
        response = self.client.post(
            '/token/',
            {'username': 'sara@example.com', 'password': 'nope-nope-nope'},
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
        user = User.objects.create_user('u1', 'u1@example.com', 'Old-pass-123')
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
        user = User.objects.create_user('u2', 'u2@example.com', 'Old-pass-123')
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

        User.objects.create_user('u3', 'u3@example.com', 'Old-pass-123')
        with override_settings(THIRD_SIDE_FE_URL='https://fe.test'), mock.patch(
            'third_side.views.AuthViews.SEND_EMAIL', True
        ), mock.patch('third_side.views.AuthViews.send_email') as send:
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
