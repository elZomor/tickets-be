from datetime import date, timedelta

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from third_side.models import (
    Certificate,
    Follow,
    LabProgram,
    LabRegistration,
    Notification,
    ThirdSideUser,
)
from third_side.services import certificates


def make_program(**extra):
    today = timezone.localdate()
    data = dict(
        slug='applied-criticism',
        slug_i18n={'ar': 'النقد-التطبيقي', 'en': 'applied-criticism'},
        title_i18n={'ar': 'النقد التطبيقي', 'en': 'Applied Criticism'},
        starts_on=today + timedelta(days=10),
        ends_on=today + timedelta(days=12),
        registration_mode='direct',
        capacity=1,
        is_published=True,
        cert_program_title_i18n={'ar': '*النقد التطبيقي* في النشرات'},
        cert_details_i18n={'ar': ['٣ أيام', '٩ ساعات']},
    )
    data.update(extra)
    return LabProgram.objects.create(**data)


@override_settings(THIRD_SIDE_NOTIFY_EAGER=True)
class LabProgramApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.program = make_program()
        cls.draft = make_program(
            slug='draft', slug_i18n={}, title_i18n={'ar': 'مسودة'}, is_published=False
        )
        cls.a = ThirdSideUser.objects.create_user(
            'a@example.com', 'pw-12345678', name='علي', email_verified=True
        )
        cls.b = ThirdSideUser.objects.create_user(
            'b@example.com', 'pw-12345678', name='بسمة', email_verified=True,
            gender='female',
        )
        cls.unverified = ThirdSideUser.objects.create_user('u@example.com', 'pw')
        cls.editor = ThirdSideUser.objects.create_user(
            'e@example.com', 'pw', is_superuser=True
        )

    def setUp(self):
        cache.clear()

    def test_public_list_hides_drafts(self):
        response = self.client.get('/third_side/lab-programs?lang=en')
        self.assertEqual(response.status_code, 200)
        slugs = [p['slug'] for p in response.data['results']]
        self.assertEqual(slugs, ['applied-criticism'])
        item = response.data['results'][0]
        self.assertEqual(item['title'], 'Applied Criticism')
        self.assertEqual(item['registration']['state'], 'open')
        self.assertEqual(item['registration']['seats_left'], 1)
        self.assertEqual(item['paths']['ar'], '/ar/مختبر-الضلع/النقد-التطبيقي')

    def test_by_slug_any_locale(self):
        response = self.client.get(
            '/third_side/lab-programs/by-slug/النقد-التطبيقي?lang=ar'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('sessions', response.data)
        self.assertEqual(
            self.client.get('/third_side/lab-programs/by-slug/draft').status_code, 404
        )

    def test_direct_registration_seats_then_waitlists(self):
        self.client.force_authenticate(self.a)
        url = f'/third_side/lab-programs/{self.program.pk}/registration'
        self.assertEqual(self.client.post(url, {}).data['status'], 'accepted')
        self.client.force_authenticate(self.b)
        self.assertEqual(self.client.post(url, {}).data['status'], 'waitlisted')
        # A cancels: B moves up and is told.
        self.client.force_authenticate(self.a)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete(url).data['status'], 'cancelled')
        reg_b = LabRegistration.objects.get(user=self.b)
        self.assertEqual(reg_b.status, 'accepted')
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.b, type='lab_registration'
            ).exists()
        )

    def test_application_needs_motivation_and_verified_email(self):
        program = make_program(slug='apply', slug_i18n={}, registration_mode='application')
        url = f'/third_side/lab-programs/{program.pk}/registration'
        self.client.force_authenticate(self.unverified)
        self.assertEqual(self.client.post(url, {'motivation': 'x'}).status_code, 403)
        self.client.force_authenticate(self.a)
        self.assertEqual(self.client.post(url, {}).status_code, 400)
        response = self.client.post(url, {'motivation': 'I write', 'phone': '010'})
        self.assertEqual(response.data['status'], 'pending')

    def test_closed_program_refuses(self):
        program = make_program(slug='closed', slug_i18n={}, registration_mode='closed')
        self.client.force_authenticate(self.a)
        response = self.client.post(
            f'/third_side/lab-programs/{program.pk}/registration', {}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'closed')

    def test_reader_cannot_write_programs(self):
        self.client.force_authenticate(self.a)
        response = self.client.post(
            '/third_side/lab-programs', {'title_i18n': {'ar': 'x'}}, format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_creates_program_with_slugs(self):
        self.client.force_authenticate(self.editor)
        response = self.client.post(
            '/third_side/lab-programs',
            {
                'title_i18n': {'ar': 'ورشة الكتابة', 'en': 'Writing Lab'},
                'kind': 'masterclass',
                'starts_on': '2027-01-01',
                'ends_on': '2027-01-02',
                'sessions': [{'date': '2027-01-01', 'title_i18n': {'en': 'Day 1'}}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['slug'], 'writing-lab')
        self.assertEqual(response.data['slug_i18n']['ar'], 'ورشة-الكتابة')

    def test_follow_lab_and_hear_of_new_programs(self):
        self.client.force_authenticate(self.a)
        self.assertEqual(self.client.put('/third_side/follows/lab/0').status_code, 201)
        follows = self.client.get('/third_side/follows?lang=en').data
        self.assertEqual(follows[0]['name'], 'Third Side Lab')
        with self.captureOnCommitCallbacks(execute=True):
            make_program(slug='new-one', slug_i18n={})
        self.assertTrue(
            Notification.objects.filter(recipient=self.a, type='new_lab_program').exists()
        )


@override_settings(THIRD_SIDE_NOTIFY_EAGER=True)
class CertificateTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.program = make_program(capacity=None)
        cls.a = ThirdSideUser.objects.create_user(
            'a@example.com', 'pw-12345678', name='<b>علي</b>', email_verified=True
        )
        cls.b = ThirdSideUser.objects.create_user(
            'b@example.com', 'pw-12345678', name='بسمة', email_verified=True,
            gender='female',
        )
        cls.editor = ThirdSideUser.objects.create_user(
            'e@example.com', 'pw', is_superuser=True
        )
        cls.reg_a = LabRegistration.objects.create(
            program=cls.program, user=cls.a, status='accepted', attended=True
        )
        cls.reg_b = LabRegistration.objects.create(
            program=cls.program, user=cls.b, status='accepted', attended=False
        )

    def setUp(self):
        cache.clear()

    def issue(self):
        self.client.force_authenticate(self.editor)
        return self.client.post(
            f'/third_side/lab-programs/{self.program.pk}/issue-certificates'
        )

    def test_issue_only_attended_once(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.issue().data['issued'], 1)
        self.assertEqual(self.issue().data['issued'], 0)
        certificate = Certificate.objects.get()
        self.assertEqual(certificate.user, self.a)
        self.assertEqual(len(certificate.code), 10)
        self.assertTrue(
            Notification.objects.filter(recipient=self.a, type='new_certificate').exists()
        )

    def test_html_escapes_and_accents(self):
        self.issue()
        code = Certificate.objects.get().code
        self.client.force_authenticate(None)
        response = self.client.get(f'/third_side/certificates/{code}/html')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('&lt;b&gt;علي&lt;/b&gt;', html)
        self.assertIn('<span class="accent">النقد التطبيقي</span>', html)
        self.assertIn('<svg', html)
        self.assertIn('٣ أيام', html)

    def test_feminine_verb(self):
        LabRegistration.objects.filter(pk=self.reg_b.pk).update(attended=True)
        self.issue()
        certificate = Certificate.objects.get(user=self.b)
        self.assertEqual(certificate.context['completed_verb'], 'أتمّت')

    def test_verify_and_mine(self):
        self.issue()
        code = Certificate.objects.get().code
        self.client.force_authenticate(None)
        data = self.client.get(f'/third_side/certificates/verify/{code}?lang=en').data
        self.assertTrue(data['valid'])
        self.assertEqual(data['program']['title'], 'Applied Criticism')
        self.client.force_authenticate(self.a)
        mine = self.client.get('/third_side/certificates/mine').data
        self.assertEqual(mine[0]['code'], code)
        self.assertEqual(mine[0]['english']['status'], 'none')
        self.client.force_authenticate(self.b)
        self.assertEqual(self.client.get('/third_side/certificates/mine').data, [])

    def test_english_waits_for_program_text_then_issues(self):
        self.issue()
        code = Certificate.objects.get().code
        self.client.force_authenticate(self.a)
        url = f'/third_side/certificates/{code}/english'
        self.assertEqual(self.client.post(url, {'name': 'علي'}).status_code, 400)
        # The program has Arabic certificate details only: held.
        response = self.client.post(url, {'name': 'Ali Hassan'})
        self.assertEqual(response.status_code, 202)
        self.program.cert_details_i18n = {'ar': ['٣ أيام'], 'en': ['3 days']}
        self.program.save()
        english = Certificate.objects.get(language='en')
        self.assertEqual(english.participant_name, 'Ali Hassan')
        self.assertEqual(english.source.code, code)
        # Asking again returns the same one.
        response = self.client.post(url, {'name': 'Ali H'})
        self.assertEqual(response.data['code'], english.code)
        html = self.client.get(f'/third_side/certificates/{english.code}/html')
        self.assertIn('has successfully attended', html.content.decode())

    def test_english_needs_own_arabic_certificate(self):
        self.issue()
        code = Certificate.objects.get().code
        self.client.force_authenticate(self.b)
        response = self.client.post(
            f'/third_side/certificates/{code}/english', {'name': 'Basma'}
        )
        self.assertEqual(response.status_code, 404)

    def test_revoked_is_invalid(self):
        self.issue()
        certificate = Certificate.objects.get()
        self.client.patch(
            f'/third_side/certificates/{certificate.pk}', {'revoked': True}, format='json'
        )
        self.client.force_authenticate(None)
        data = self.client.get(f'/third_side/certificates/verify/{certificate.code}').data
        self.assertFalse(data['valid'])
        self.assertEqual(
            self.client.get(f'/third_side/certificates/{certificate.code}/html').status_code,
            404,
        )

    def test_template_preview_and_bad_syntax(self):
        self.client.force_authenticate(self.editor)
        templates = self.client.get('/third_side/certificate-templates').data
        self.assertEqual({t['language'] for t in templates}, {'ar', 'en'})
        response = self.client.post(
            '/third_side/certificate-templates/preview',
            {'html': '<p>{{ participant_name }}</p>', 'language': 'en'},
            format='json',
        )
        self.assertIn('Mohamed', response.data['html'])
        response = self.client.patch(
            f"/third_side/certificate-templates/{templates[0]['id']}",
            {'html': '{% if %}'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_date_formats(self):
        self.assertEqual(certificates.format_date(date(2026, 11, 28), 'ar'), '٢٨ نوفمبر ٢٠٢٦')
        self.assertEqual(certificates.format_date(date(2026, 11, 28), 'en'), '28 November 2026')
