from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from third_side.models import OutgoingEmail, Role, SiteSettings, ThirdSideUser
from third_side.services import mail

BODY = {
    'to': ['Reader@Example.com', 'reader@example.com'],
    'cc': ['reader@example.com', 'cc@example.com'],
    'subject': 'Hello',
    'direction': 'rtl',
    'doc': {'root': {'children': []}},
    'html': '<p style="margin:0">مرحبا</p>',
}


def brevo_response(status_code=201, data=None):
    response = mock.Mock(status_code=status_code, text='')
    response.json.return_value = data or {'messageId': '<id@brevo>'}
    return response


@override_settings(BREVO_API_KEY='key', THIRD_SIDE_MAIL_DOMAIN='third-side.org')
class EmailTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = ThirdSideUser.objects.create_user(
            'mohamed.elzomor@third-side.org', 'pw', name='Mohamed', role=Role.EDITOR
        )
        cls.outsider = ThirdSideUser.objects.create_user(
            'editor@gmail.com', 'pw', role=Role.EDITOR
        )
        cls.reader = ThirdSideUser.objects.create_user('r@third-side.org', 'pw')

    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.client.force_authenticate(self.editor)

    @mock.patch('third_side.services.mail.requests.post')
    def test_send_uses_editor_address_and_records_it(self, post):
        post.return_value = brevo_response()
        response = self.client.post('/third_side/emails', BODY, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        payload = post.call_args.kwargs['json']
        self.assertEqual(
            payload['sender'],
            {'email': 'mohamed.elzomor@third-side.org', 'name': 'Mohamed'},
        )
        self.assertEqual(payload['replyTo']['email'], 'mohamed.elzomor@third-side.org')
        self.assertEqual(payload['to'], [{'email': 'reader@example.com'}])
        self.assertEqual(payload['cc'], [{'email': 'cc@example.com'}])
        self.assertIn('dir="rtl"', payload['htmlContent'])
        self.assertIn('مرحبا', payload['htmlContent'])
        self.assertEqual(post.call_args.kwargs['headers']['api-key'], 'key')
        sent = OutgoingEmail.objects.get()
        self.assertEqual(
            (sent.status, sent.provider_message_id), ('sent', '<id@brevo>')
        )
        self.assertEqual(sent.sender, self.editor)
        rows = self.client.get('/third_side/emails').data['results']
        self.assertEqual(rows[0]['subject'], 'Hello')

    @mock.patch('third_side.services.mail.requests.post')
    def test_brevo_failure_is_kept_and_reported(self, post):
        post.return_value = brevo_response(400, {'message': 'sender not valid'})
        response = self.client.post('/third_side/emails', BODY, format='json')
        self.assertEqual(response.status_code, 502)
        sent = OutgoingEmail.objects.get()
        self.assertEqual(sent.status, 'failed')
        self.assertIn('sender not valid', sent.error)

    @mock.patch('third_side.services.mail.requests.post')
    def test_test_send_goes_to_sender_only_and_is_not_kept(self, post):
        post.return_value = brevo_response()
        response = self.client.post(
            '/third_side/emails', {**BODY, 'to': [], 'test': True}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['to'], [{'email': 'mohamed.elzomor@third-side.org'}])
        self.assertNotIn('cc', payload)
        self.assertTrue(payload['subject'].startswith('[Test]'))
        self.assertFalse(OutgoingEmail.objects.exists())

    @mock.patch('third_side.services.mail.requests.post')
    def test_rejections(self, post):
        cases = [
            {**BODY, 'audience': 'subscribers'},
            {**BODY, 'to': []},
            {**BODY, 'to': ['not-an-email']},
            {**BODY, 'to': [f'u{i}@example.com' for i in range(51)]},
        ]
        for body in cases:
            response = self.client.post('/third_side/emails', body, format='json')
            self.assertEqual(response.status_code, 400, body)
        post.assert_not_called()

    @mock.patch('third_side.services.mail.requests.post')
    def test_sender_must_be_on_the_mail_domain(self, post):
        self.client.force_authenticate(self.outsider)
        response = self.client.post('/third_side/emails', BODY, format='json')
        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    def test_editors_only(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get('/third_side/emails').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/third_side/emails').status_code, 401)

    @override_settings(BREVO_API_KEY='')
    def test_missing_key_raises(self):
        with self.assertRaises(mail.MailError):
            mail.send('a@third-side.org', 'A', ['b@example.com'], 's', '<p></p>')


@override_settings(
    BREVO_API_KEY='key',
    THIRD_SIDE_MAIL_DOMAIN='third-side.org',
    THIRD_SIDE_FE_URL='https://third-side.org',
    MEDIA_PUBLIC_HOST='https://media.test',
)
class SignatureTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = ThirdSideUser.objects.create_user(
            'mohamed.elzomor@third-side.org', 'pw', name='Mohamed', role=Role.EDITOR
        )
        cls.editor.avatar.name = 'third_side/avatars/me.png'
        cls.editor.save()
        settings = SiteSettings.load()
        settings.social = [
            {'network': 'facebook', 'url': 'https://facebook.com/thirdside'},
            {'network': 'x', 'url': 'javascript:alert(1)'},
        ]
        settings.save()

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.editor)

    def put(self, **kwargs):
        body = {
            'name': {'ar': 'محمد الزمر', 'en': 'Mohamed Elzomor', 'ro': 'x'},
            'title': {'ar': 'رئيس التحرير', 'en': ''},
            'phone': ' +20 100 000 0000 ',
        }
        body.update(kwargs)
        return self.client.put('/third_side/profile/me/signature', body, format='json')

    def test_save_and_read_back(self):
        response = self.put()
        self.assertEqual(response.status_code, 200, response.data)
        self.editor.refresh_from_db()
        self.assertEqual(
            self.editor.signature,
            {
                'name': {'ar': 'محمد الزمر', 'en': 'Mohamed Elzomor'},
                'title': {'ar': 'رئيس التحرير'},
                'phone': '+20 100 000 0000',
                'show_photo': True,
                'show_social': True,
            },
        )
        data = self.client.get('/third_side/profile/me/signature').data
        self.assertEqual(data['name']['ar'], 'محمد الزمر')

    def test_get_defaults_when_empty(self):
        data = self.client.get('/third_side/profile/me/signature').data
        self.assertEqual((data['phone'], data['show_photo']), ('', True))

    def test_too_long_is_rejected(self):
        self.assertEqual(self.put(title={'ar': 'x' * 121}).status_code, 400)

    def test_preview_has_signature_per_language(self):
        self.put()
        rtl = self.client.post(
            '/third_side/emails/preview', {'html': '<p>نص</p>'}, format='json'
        ).data['html']
        self.assertIn('محمد الزمر', rtl)
        self.assertIn('رئيس التحرير', rtl)
        self.assertIn('https://media.test/third_side/avatars/me.png', rtl)
        self.assertIn('tel:+201000000000', rtl)
        self.assertIn('https://facebook.com/thirdside', rtl)
        self.assertNotIn('javascript:', rtl)
        ltr = self.client.post(
            '/third_side/emails/preview',
            {'html': '<p>x</p>', 'direction': 'ltr'},
            format='json',
        ).data['html']
        self.assertIn('Mohamed Elzomor', ltr)
        self.assertIn('رئيس التحرير', ltr)  # no English title: falls back

    def test_switches(self):
        self.put(show_photo=False, show_social=False)
        html = self.client.post(
            '/third_side/emails/preview', {'html': '<p>x</p>'}, format='json'
        ).data['html']
        self.assertNotIn('avatars/me.png', html)
        self.assertNotIn('facebook', html)
        bare = self.client.post(
            '/third_side/emails/preview',
            {'html': '<p>x</p>', 'signature': False},
            format='json',
        ).data['html']
        self.assertNotIn('محمد', bare)

    @mock.patch('third_side.services.mail.requests.post')
    def test_sent_mail_carries_signature_unless_off(self, post):
        post.return_value = brevo_response()
        self.put()
        body = {'to': ['a@example.com'], 'subject': 's', 'html': '<p>x</p>'}
        self.client.post('/third_side/emails', body, format='json')
        self.assertIn('محمد الزمر', post.call_args.kwargs['json']['htmlContent'])
        self.client.post(
            '/third_side/emails', {**body, 'signature': False}, format='json'
        )
        self.assertNotIn('محمد الزمر', post.call_args.kwargs['json']['htmlContent'])
