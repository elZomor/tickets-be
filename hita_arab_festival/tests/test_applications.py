import json
import shutil
import tempfile
from datetime import date

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from hita_arab_festival.models import Application, ArabFestival

MEDIA_ROOT = tempfile.mkdtemp()
URL = '/hita_arab_festival/applications'


@override_settings(
    MEDIA_ROOT=MEDIA_ROOT,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'
        },
    },
)
class ApplicationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.festival = ArabFestival.objects.create(
            name='مهرجان',
            description='desc',
            start_date=date(2027, 1, 1),
            end_date=date(2027, 1, 10),
            applications_open=True,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def payload(self, **overrides):
        data = {
            'email': 'Director@Example.com',
            'show_name': 'العرض المسرحي',
            'director_name': 'أحمد محمد',
            'department': 'ACTING_DIRECTING',
            'study_type': 'CREDIT_HOURS',
            'study_phase': 'UNDERGRAD',
            'author': 'توفيق الحكيم',
            'dramaturgy': '',
            'mobile': '01012345678',
            'whatsapp': '+20 101 234 5678',
            'actors': json.dumps(['محمود', 'سارة']),
            'script': SimpleUploadedFile('script.pdf', b'%PDF-1.4', 'application/pdf'),
            'directorial_vision': 'رؤية إخراجية للعرض.',
            'show_summary': 'ملخص العرض، وفيه تفاصيل.',
            'national_id': SimpleUploadedFile('id.jpg', b'\xff\xd8\xff', 'image/jpeg'),
        }
        data.update(overrides)
        return data

    def post(self, **overrides):
        return self.client.post(URL, self.payload(**overrides), format='multipart')

    def test_status_reports_open_festival(self):
        response = self.client.get(f'{URL}/status')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data']['open'])
        self.assertEqual(
            str(response.data['data']['festival_start_date']), '2027-01-01'
        )
        self.assertEqual(str(response.data['data']['festival_end_date']), '2027-01-10')

    def test_submits_application(self):
        response = self.post()
        self.assertEqual(response.status_code, 201, response.data)
        application = Application.objects.get()
        self.assertEqual(application.email, 'director@example.com')
        self.assertEqual(application.whatsapp, '01012345678')
        self.assertEqual(application.actors, ['محمود', 'سارة'])
        self.assertEqual(application.festival, self.festival)
        self.assertIsNone(application.user)

    def test_rejects_latin_text(self):
        response = self.post(show_name='Hamlet', actors=json.dumps(['John']))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['data']['show_name'], ['ARABIC_ONLY'])
        self.assertEqual(response.data['data']['actors'], ['ARABIC_ONLY'])

    def test_optional_dramaturgy_must_be_arabic_when_given(self):
        response = self.post(dramaturgy='Someone')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['data']['dramaturgy'], ['ARABIC_ONLY'])

    def test_rejects_invalid_mobile(self):
        response = self.post(mobile='12345')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['data']['mobile'], ['INVALID_MOBILE'])

    def test_accepts_international_whatsapp(self):
        response = self.post(whatsapp='+966 50 123 4567')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Application.objects.get().whatsapp, '+966501234567')

    def test_accepts_international_whatsapp_with_00_prefix(self):
        response = self.post(whatsapp='00971501234567')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Application.objects.get().whatsapp, '+971501234567')

    def test_rejects_invalid_whatsapp(self):
        for whatsapp in ('12345', '966501234567', '+12'):
            response = self.post(whatsapp=whatsapp)
            self.assertEqual(response.status_code, 400, whatsapp)
            self.assertEqual(response.data['data']['whatsapp'], ['INVALID_WHATSAPP'])

    def test_rejects_wrong_file_type(self):
        response = self.post(
            script=SimpleUploadedFile('script.exe', b'x', 'application/octet-stream')
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['data']['script'], ['INVALID_FILE_TYPE'])

    def test_rejects_missing_required_field(self):
        data = self.payload()
        del data['author']
        response = self.client.post(URL, data, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['data']['author'], ['required'])

    def test_requires_study_phase(self):
        data = self.payload()
        del data['study_phase']
        response = self.client.post(URL, data, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['data']['study_phase'], ['required'])

    def test_rejects_invalid_study_phase(self):
        response = self.post(study_phase='PHD')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['data']['study_phase'], ['invalid_choice'])

    def test_one_application_per_email_per_festival(self):
        self.assertEqual(self.post().status_code, 201)
        response = self.post(email='director@example.com')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['message'], 'ALREADY_APPLIED')

    def test_hidden_festival_still_accepts_applications(self):
        ArabFestival.objects.update(is_visible=False)
        self.assertEqual(self.post().status_code, 201)
        status = self.client.get(f'{URL}/status').data['data']
        self.assertTrue(status['open'])
        self.assertEqual(status['festival_name'], 'مهرجان')

    def test_status_has_no_application_for_anonymous(self):
        self.post()
        self.assertIsNone(self.client.get(f'{URL}/status').data['data']['my_application'])

    def test_status_shows_application_of_logged_in_user_by_email(self):
        self.assertEqual(self.post().status_code, 201)  # submitted anonymously
        user = User.objects.create(username='u1', email='director@example.com')
        self.client.force_authenticate(user)
        mine = self.client.get(f'{URL}/status').data['data']['my_application']
        self.assertEqual(mine['show_name'], 'العرض المسرحي')
        self.assertEqual(mine['status'], 'PENDING')

    def test_status_shows_application_linked_to_user(self):
        user = User.objects.create(username='u2', email='other@example.com')
        self.client.force_authenticate(user)
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(Application.objects.get().user, user)
        mine = self.client.get(f'{URL}/status').data['data']['my_application']
        self.assertIsNotNone(mine)

    def test_status_ignores_other_users_applications(self):
        self.post()
        user = User.objects.create(username='u3', email='someone@example.com')
        self.client.force_authenticate(user)
        self.assertIsNone(self.client.get(f'{URL}/status').data['data']['my_application'])

    def test_closed_when_no_festival_is_open(self):
        ArabFestival.objects.update(applications_open=False)
        response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['message'], 'APPLICATIONS_CLOSED')
        self.assertFalse(self.client.get(f'{URL}/status').data['data']['open'])
