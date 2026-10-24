from datetime import date, timedelta

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from third_side.models import ActivityLog, Ad, ThirdSideUser
from third_side.tests.test_site_content import ad

HOST = 'https://media.play-cast.com'
KEY = 'third_side/media/banner.png'
SIGNED = f'https://bucket.s3.amazonaws.com/{KEY}?X-Amz-Signature=' + 'f' * 400


@override_settings(MEDIA_PUBLIC_HOST=HOST)
class AdAdminTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = ThirdSideUser.objects.create_user(
            'e@example.com', 'pw', is_superuser=True
        )
        cls.reader = ThirdSideUser.objects.create_user('r@example.com', 'pw')
        cls.ad = ad('fest', impressions=10, clicks=2)

    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.client.force_authenticate(self.editor)

    def body(self, **kwargs):
        today = date.today()
        data = {
            'type': 'event',
            'name': 'Night of criticism',
            'url': 'https://example.com/event',
            'internal': False,
            'locales': ['en', 'ar'],
            'starts_at': today.isoformat(),
            'ends_at': (today + timedelta(days=7)).isoformat(),
            'weight': 2,
            'alt': {'ar': 'أمسية', 'en': 'An evening', 'ro': ''},
            'images': {'ar': {'rect': SIGNED, 'slim': ''}, 'en': {'column': SIGNED}},
            'is_active': True,
        }
        data.update(kwargs)
        return data

    def test_create_stores_keys_and_reads_media_urls(self):
        response = self.client.post('/third_side/ads', self.body(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        created = Ad.objects.get(pk=response.data['id'])
        self.assertEqual(created.images, {'ar': {'rect': KEY}, 'en': {'column': KEY}})
        self.assertEqual(created.locales, ['ar', 'en'])  # site order
        self.assertEqual(created.alt, {'ar': 'أمسية', 'en': 'An evening'})
        self.assertEqual(response.data['images']['ar']['rect'], f'{HOST}/{KEY}')
        self.assertTrue(
            ActivityLog.objects.filter(object_type='ad', object_id=str(created.pk)).exists()
        )

    def test_list_includes_counters_and_counters_are_read_only(self):
        rows = self.client.get('/third_side/ads').data['results']
        row = next(r for r in rows if r['id'] == self.ad.pk)
        self.assertEqual((row['impressions'], row['clicks']), (10, 2))
        response = self.client.patch(
            f'/third_side/ads/{self.ad.pk}', {'clicks': 999, 'weight': 5}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.ad.refresh_from_db()
        self.assertEqual((self.ad.clicks, self.ad.weight), (2, 5))

    def test_validation(self):
        bad = [
            {'locales': []},
            {'locales': ['fr']},
            {'images': {'ar': {'huge': 'x.png'}}},
            {'ends_at': (date.today() - timedelta(days=1)).isoformat()},
        ]
        for patch in bad:
            response = self.client.post('/third_side/ads', self.body(**patch), format='json')
            self.assertEqual(response.status_code, 400, patch)

    def test_delete(self):
        response = self.client.delete(f'/third_side/ads/{self.ad.pk}')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Ad.objects.filter(pk=self.ad.pk).exists())

    def test_editors_only_and_public_routes_untouched(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get('/third_side/ads').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/third_side/ads').status_code, 401)
        pick = self.client.get('/third_side/ads/pick?lang=en&size=banner')
        self.assertEqual(pick.status_code, 200)
        self.assertEqual(
            self.client.post(f'/third_side/ads/{self.ad.pk}/click').status_code, 204
        )

    def test_pick_returns_media_urls_for_stored_keys(self):
        Ad.objects.exclude(pk=self.ad.pk).delete()
        self.ad.images = {'en': {'column': KEY}}
        self.ad.save()
        self.client.force_authenticate(None)
        data = self.client.get('/third_side/ads/pick?lang=en&size=column').data
        self.assertEqual(data['image'], f'{HOST}/{KEY}')
        self.assertEqual(data['images'], {'column': f'{HOST}/{KEY}'})
