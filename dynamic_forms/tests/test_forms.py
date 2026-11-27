import shutil
import tempfile
from datetime import timedelta
from io import BytesIO

from datetime import date

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APITestCase

from alt_spaces_festival.models import AltSpacesFestival
from dynamic_forms.admin import build_workbook
from hita_arab_festival.models import ArabFestival
from dynamic_forms.models import (
    FieldPreset,
    FieldType,
    Form,
    FormField,
    FormResponse,
    UniqueBy,
)

MEDIA_ROOT = tempfile.mkdtemp()
INSTITUTES = ['فنون مسرحية', 'سينما', 'إسكندرية']
YEARS = ['الأولى', 'الثانية', 'خريج']


@override_settings(
    MEDIA_ROOT=MEDIA_ROOT,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'
        },
    },
)
class DynamicFormTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.festival = ArabFestival.objects.create(
            name='مهرجان',
            description='desc',
            start_date=date(2027, 1, 1),
            end_date=date(2027, 1, 10),
        )
        self.form = Form.objects.create(
            arab_festival=self.festival,
            slug='masterclass',
            title='ماستر كلاس',
            notice='الحضور مقتصر على طلاب أكاديمية الفنون فقط',
            unique_by=UniqueBy.FIELD,
            unique_field_key='mobile',
        )
        fields = [
            dict(key='name', label='الاسم', type=FieldType.TEXT),
            dict(
                key='institute',
                label='المعهد',
                type=FieldType.SELECT,
                options=INSTITUTES,
            ),
            dict(key='year', label='الفرقة', type=FieldType.RADIO, options=YEARS),
            dict(
                key='mobile',
                label='رقم موبايل',
                type=FieldType.PHONE,
                preset=FieldPreset.EGYPT_MOBILE,
            ),
            dict(
                key='interests',
                label='الاهتمامات',
                type=FieldType.CHECKBOXES,
                options=['تمثيل', 'إخراج'],
                required=False,
            ),
            dict(
                key='id_card',
                label='صورة البطاقة',
                type=FieldType.FILE,
                allowed_extensions=['.jpg', 'png', '.pdf'],
                max_file_mb=1,
            ),
            dict(key='consent', label='أنا طالب في الأكاديمية', type=FieldType.CONSENT),
        ]
        for order, field in enumerate(fields):
            FormField.objects.create(form=self.form, order=order, **field)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    @property
    def url(self):
        return f'/hita_arab_festival/forms/{self.form.slug}'

    def payload(self, **overrides):
        data = {
            'name': 'مريم عبدالعزيز',
            'institute': 'فنون مسرحية',
            'year': 'الأولى',
            'mobile': '٠١١٤٩٥٨٦٤٣٨ ',
            'interests': ['إخراج', 'تمثيل'],
            'id_card': SimpleUploadedFile('id.JPG', b'\xff\xd8\xff', 'image/jpeg'),
            'consent': 'true',
        }
        data.update(overrides)
        return {k: v for k, v in data.items() if v is not None}

    def post(self, **overrides):
        return self.client.post(
            f'{self.url}/responses', self.payload(**overrides), format='multipart'
        )

    def assert_error(self, response, key, code):
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data['message'], 'VALIDATION_ERROR')
        self.assertEqual(response.data['data'][key], [code])

    # Schema

    def test_schema_lists_fields_in_order(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.data['data']
        self.assertTrue(data['open'])
        self.assertIsNone(data['closed_reason'])
        self.assertEqual(
            [f['key'] for f in data['fields']],
            ['name', 'institute', 'year', 'mobile', 'interests', 'id_card', 'consent'],
        )
        self.assertEqual(data['fields'][1]['options'], INSTITUTES)
        self.assertEqual(
            data['fields'][5]['allowed_extensions'], ['.jpg', '.png', '.pdf']
        )
        self.assertNotIn('options', data['fields'][0])

    def test_unknown_form_is_404(self):
        self.assertEqual(
            self.client.get('/hita_arab_festival/forms/nope').status_code, 404
        )

    def test_form_is_only_served_under_its_festival(self):
        other = '/alt_spaces_festival/forms/masterclass'
        self.assertEqual(self.client.get(other).status_code, 404)
        self.assertEqual(self.client.post(f'{other}/responses', {}).status_code, 404)

    def test_form_must_have_exactly_one_festival(self):
        from django.core.exceptions import ValidationError

        self.form.full_clean()
        alt = AltSpacesFestival.objects.create(
            name='alt', description='d', start_date=date(2027, 1, 1), end_date=date(2027, 1, 2)
        )
        self.form.alt_spaces_festival = alt
        with self.assertRaises(ValidationError):
            self.form.full_clean()
        self.form.arab_festival = None
        self.form.alt_spaces_festival = None
        with self.assertRaises(ValidationError):
            self.form.full_clean()

    # Festival list

    def test_festival_lists_only_its_open_forms(self):
        Form.objects.create(
            arab_festival=self.festival, slug='draft', title='draft', is_active=False
        )
        Form.objects.create(
            arab_festival=self.festival,
            slug='past',
            title='past',
            closes_at=timezone.now() - timedelta(days=1),
        )
        other = ArabFestival.objects.create(
            name='other',
            description='d',
            start_date=date(2027, 1, 1),
            end_date=date(2027, 1, 2),
        )
        Form.objects.create(arab_festival=other, slug='other', title='other')
        response = self.client.get(
            '/hita_arab_festival/forms', {'festival': self.festival.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([f['slug'] for f in response.data['data']], ['masterclass'])
        self.assertEqual(response.data['data'][0]['title'], 'ماستر كلاس')
        alt = self.client.get(
            '/alt_spaces_festival/forms', {'festival': self.festival.pk}
        )
        self.assertEqual(alt.data['data'], [])
        self.assertEqual(self.client.get('/hita_arab_festival/forms').status_code, 400)

        everything = self.client.get(
            '/hita_arab_festival/forms', {'festival': self.festival.pk, 'all': '1'}
        )
        self.assertEqual(
            [(f['slug'], f['status']) for f in everything.data['data']],
            [('past', 'CLOSED'), ('masterclass', 'OPEN')],
        )

    def test_schema_includes_english_text(self):
        self.form.title_en = 'Masterclass'
        self.form.warning = 'بالعربية فقط'
        self.form.save()
        field = self.form.fields.get(key='year')
        field.label_en = 'Year'
        field.options_en = ['First', 'Second', 'Graduate']
        field.save()
        data = self.client.get(self.url).data['data']
        self.assertEqual(data['title_en'], 'Masterclass')
        self.assertEqual(data['warning'], 'بالعربية فقط')
        year = next(f for f in data['fields'] if f['key'] == 'year')
        self.assertEqual(year['label_en'], 'Year')
        self.assertEqual(year['options_en'], ['First', 'Second', 'Graduate'])

    def test_english_options_must_match_options(self):
        from django.core.exceptions import ValidationError

        field = self.form.fields.get(key='year')
        field.options_en = ['First']
        with self.assertRaises(ValidationError):
            field.full_clean()

    # Submission

    def test_saves_response_with_normalized_values_and_file(self):
        response = self.post()
        self.assertEqual(response.status_code, 201, response.data)
        saved = FormResponse.objects.get()
        self.assertEqual(saved.answers['mobile'], '01149586438')
        self.assertEqual(saved.answers['interests'], ['تمثيل', 'إخراج'])
        self.assertIs(saved.answers['consent'], True)
        self.assertNotIn('id_card', saved.answers)
        self.assertEqual(saved.unique_value, 'mobile:01149586438')
        stored = saved.files.get()
        self.assertEqual(stored.field_key, 'id_card')
        self.assertEqual(stored.original_name, 'id.JPG')
        self.assertTrue(stored.file.name.startswith('media/forms/masterclass/id_card/'))

    def test_required_fields(self):
        response = self.post(name='  ', id_card=None, consent=None)
        self.assertEqual(response.status_code, 400)
        errors = response.data['data']
        self.assertEqual(errors['name'], ['required'])
        self.assertEqual(errors['id_card'], ['required'])
        self.assertEqual(errors['consent'], ['required'])
        self.assertNotIn('interests', errors)

    def test_optional_field_can_be_empty(self):
        response = self.post(interests=None)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(FormResponse.objects.get().answers['interests'], [])

    def test_rejects_invalid_mobile(self):
        self.assert_error(self.post(mobile='12345'), 'mobile', 'INVALID_MOBILE')

    def test_rejects_unknown_option(self):
        self.assert_error(self.post(institute='هندسة'), 'institute', 'INVALID_OPTION')
        self.assert_error(self.post(interests=['غناء']), 'interests', 'INVALID_OPTION')

    def test_rejects_wrong_file_type(self):
        upload = SimpleUploadedFile('x.exe', b'x', 'application/octet-stream')
        self.assert_error(self.post(id_card=upload), 'id_card', 'INVALID_FILE_TYPE')

    def test_rejects_large_file(self):
        upload = SimpleUploadedFile('id.png', b'x' * (1024 * 1024 + 1), 'image/png')
        self.assert_error(self.post(id_card=upload), 'id_card', 'FILE_TOO_LARGE')

    def test_rejects_too_many_files(self):
        files = [
            SimpleUploadedFile('a.png', b'x', 'image/png'),
            SimpleUploadedFile('b.png', b'x', 'image/png'),
        ]
        self.assert_error(self.post(id_card=files), 'id_card', 'TOO_MANY_FILES')

    def test_pattern_and_length_rules(self):
        name = self.form.fields.get(key='name')
        name.max_length = 5
        name.save()
        self.assert_error(self.post(), 'name', 'TOO_LONG')
        name.max_length = None
        name.pattern = r'[A-Za-z ]+'
        name.save()
        self.assert_error(self.post(), 'name', 'INVALID_PATTERN')
        self.assertEqual(self.post(name='Mariam').status_code, 201)

    def test_arabic_only_preset(self):
        name = self.form.fields.get(key='name')
        name.preset = FieldPreset.ARABIC_ONLY
        name.save()
        self.assert_error(self.post(name='Mariam'), 'name', 'ARABIC_ONLY')

    def test_blocks_duplicate_field_value(self):
        self.assertEqual(self.post().status_code, 201)
        response = self.post(mobile='+201149586438')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['message'], 'ALREADY_SUBMITTED')
        self.assertEqual(FormResponse.objects.count(), 1)

    def test_allows_duplicates_when_not_unique(self):
        self.form.unique_by = UniqueBy.NONE
        self.form.save()
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 201)

    # Availability

    def test_closed_states(self):
        now = timezone.now()
        cases = [
            ({'is_active': False}, 'CLOSED'),
            ({'opens_at': now + timedelta(days=1)}, 'NOT_OPEN_YET'),
            ({'closes_at': now - timedelta(minutes=1)}, 'CLOSED'),
        ]
        for changes, reason in cases:
            reset = {'is_active': True, 'opens_at': None, 'closes_at': None}
            Form.objects.filter(pk=self.form.pk).update(**(reset | changes))
            data = self.client.get(self.url).data['data']
            self.assertFalse(data['open'], reason)
            self.assertEqual(data['closed_reason'], reason)
            response = self.post()
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data['message'], 'FORM_CLOSED')

    def test_response_cap(self):
        self.form.max_responses = 1
        self.form.save()
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.client.get(self.url).data['data']['closed_reason'], 'FULL')
        response = self.post(mobile='01012345678')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['message'], 'FORM_CLOSED')

    # Login

    def test_login_required(self):
        self.form.requires_login = True
        self.form.save()
        response = self.post()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['message'], 'LOGIN_REQUIRED')

        user = User.objects.create_user('u1', email='u1@example.com')
        self.client.force_authenticate(user)
        self.assertEqual(self.post().status_code, 201)
        saved = FormResponse.objects.get()
        self.assertEqual(saved.user, user)
        self.assertEqual(saved.email, 'u1@example.com')
        my = self.client.get(self.url).data['data']['my_response']
        self.assertEqual(my['id'], saved.id)

    def test_one_response_per_user(self):
        self.form.unique_by = UniqueBy.USER
        self.form.save()
        self.assertTrue(self.client.get(self.url).data['data']['requires_login'])
        self.assertEqual(self.post().status_code, 401)

        self.client.force_authenticate(User.objects.create_user('u2'))
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post(mobile='01012345678').status_code, 409)

    # Export

    def test_export_has_one_column_per_field(self):
        self.post()
        content = build_workbook([(self.form, self.form.responses.all())])
        sheet = load_workbook(BytesIO(content)).active
        header = [c.value for c in sheet[1]]
        self.assertEqual(header[2:], [f.label for f in self.form.fields.all()])
        row = [c.value for c in sheet[2]]
        self.assertEqual(row[2], 'مريم عبدالعزيز')
        self.assertEqual(row[6], 'تمثيل، إخراج')
        self.assertIn('media/forms/masterclass/id_card/', row[7])
        self.assertEqual(row[8], 'نعم')

    # Admin

    def test_admin_pages_and_actions(self):
        self.post()
        admin_user = User.objects.create_superuser('admin', 'a@example.com', 'pw')
        self.client.force_login(admin_user)
        base = '/admin/dynamic_forms'
        for path in (
            f'{base}/form/',
            f'{base}/form/add/',
            f'{base}/form/{self.form.pk}/change/',
            f'{base}/formresponse/',
            f'{base}/formresponse/{FormResponse.objects.get().pk}/change/',
        ):
            self.assertEqual(self.client.get(path).status_code, 200, path)

        export = self.client.post(
            f'{base}/form/',
            {'action': 'export_responses', '_selected_action': [self.form.pk]},
        )
        self.assertEqual(export.status_code, 200)
        self.assertIn('spreadsheetml', export['Content-Type'])

        self.client.post(
            f'{base}/form/',
            {'action': 'duplicate_forms', '_selected_action': [self.form.pk]},
        )
        copy = Form.objects.get(slug='masterclass-2')
        self.assertFalse(copy.is_active)
        self.assertEqual(copy.fields.count(), self.form.fields.count())
