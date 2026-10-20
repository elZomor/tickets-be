from datetime import date, timedelta

from django.core.cache import cache
from rest_framework.test import APITestCase

from third_side.models import TermsAcceptance, TermsVersion, ThirdSideUser

SIGNUP = {'name': 'Sara Ali', 'email': 'sara@example.com', 'password': 'S3cure-pass!'}


def loc(text):
    return {'ar': f'{text}-ar', 'en': f'{text}-en', 'ro': f'{text}-ro'}


def make_terms(version, days_ago=1, published=True):
    return TermsVersion.objects.create(
        version=version,
        effective_date=date.today() - timedelta(days=days_ago),
        is_published=published,
        content={
            'title': loc('title'),
            'sections': [{'heading': loc('h'), 'paragraphs': [loc('p')]}],
        },
    )


class FirstTermsMigrationTests(APITestCase):
    def test_v1_is_published_by_migration(self):
        data = self.client.get('/third_side/terms?lang=en').data
        self.assertEqual(data['version'], '1.0')
        self.assertEqual(data['effective_date'], '2026-10-01')
        self.assertEqual(len(data['sections']), 6)
        self.assertEqual(
            self.client.get('/third_side/terms').data['title'][:6], 'الشروط'
        )


class TermsApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        TermsVersion.objects.all().delete()  # drop the migration's v1.0

    def test_no_terms_is_404(self):
        self.assertEqual(self.client.get('/third_side/terms').status_code, 404)

    def test_current_is_localized_and_public(self):
        make_terms('1.0')
        data = self.client.get('/third_side/terms?lang=en').data
        self.assertEqual(data['version'], '1.0')
        self.assertEqual(data['title'], 'title-en')
        self.assertEqual(data['sections'][0]['paragraphs'], ['p-en'])
        self.assertEqual(self.client.get('/third_side/terms').data['title'], 'title-ar')

    def test_newest_published_in_force_wins(self):
        make_terms('1.0', days_ago=30)
        make_terms('1.1', days_ago=1)
        make_terms('2.0', days_ago=-5)  # not in force yet
        make_terms('1.2', days_ago=0, published=False)  # draft
        self.assertEqual(self.client.get('/third_side/terms').data['version'], '1.1')

    def test_versions_list_and_detail(self):
        make_terms('1.0', days_ago=30)
        make_terms('1.1')
        make_terms('draft', published=False)
        versions = self.client.get('/third_side/terms/versions').data
        self.assertEqual([v['version'] for v in versions], ['1.1', '1.0'])
        old = self.client.get('/third_side/terms/1.0?lang=ro').data
        self.assertEqual(old['title'], 'title-ro')
        self.assertEqual(self.client.get('/third_side/terms/draft').status_code, 404)


class SignupTermsTests(APITestCase):
    def setUp(self):
        cache.clear()
        TermsVersion.objects.all().delete()  # drop the migration's v1.0

    def test_signup_without_terms_when_none_published(self):
        response = self.client.post('/third_side/auth/signup', SIGNUP, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TermsAcceptance.objects.count(), 0)

    def test_signup_requires_current_version(self):
        make_terms('1.0')
        for body in (SIGNUP, {**SIGNUP, 'accepted_terms_version': '0.9'}):
            response = self.client.post('/third_side/auth/signup', body, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('accepted_terms_version', response.data)
        self.assertFalse(ThirdSideUser.objects.exists())

    def test_signup_records_acceptance(self):
        terms = make_terms('1.0')
        response = self.client.post(
            '/third_side/auth/signup',
            {**SIGNUP, 'accepted_terms_version': '1.0'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        acceptance = TermsAcceptance.objects.get()
        self.assertEqual(acceptance.terms, terms)
        self.assertEqual(acceptance.user.email, 'sara@example.com')

    def test_stale_version_refused_after_new_publish(self):
        make_terms('1.0', days_ago=30)
        make_terms('1.1')
        response = self.client.post(
            '/third_side/auth/signup',
            {**SIGNUP, 'accepted_terms_version': '1.0'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
