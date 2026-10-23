from django.test import SimpleTestCase, override_settings

from third_side.models import Article, Category, NavGroup, Role, ThirdSideUser
from third_side.services.media_urls import file_url, to_key, to_url
from third_side.tests.test_reader_uploads import _MediaTestCase, image

HOST = 'https://media.play-cast.com'
KEY = 'third_side/media/lit-2a394767.png'


@override_settings(MEDIA_PUBLIC_HOST=HOST)
class MediaHostTests(SimpleTestCase):
    def test_keys_resolve_through_the_media_host(self):
        self.assertEqual(to_url(KEY), f'{HOST}/{KEY}')
        self.assertEqual(
            file_url('third_side/media/a b.png'), f'{HOST}/third_side/media/a%20b.png'
        )

    def test_media_host_urls_store_as_keys(self):
        self.assertEqual(to_key(f'{HOST}/{KEY}?w=800&q=75'), KEY)


@override_settings(MEDIA_PUBLIC_HOST=HOST)
class NoRawStorageUrlsTests(_MediaTestCase):
    """Neither the admin nor the site ever gets a storage link (S3 in production)."""

    @classmethod
    def setUpTestData(cls):
        cls.editor = ThirdSideUser.objects.create_user(
            'e@example.com', 'pw', role=Role.EDITOR
        )
        group = NavGroup.objects.create(
            slug='visual', label={'en': 'Visual'}, image_url=KEY
        )
        cls.category = Category.objects.create(
            name='Cinema', slug='cinema', group=group, image_url=KEY, hero_image_url=KEY
        )

    def test_upload_returns_the_media_host_url(self):
        self.client.force_authenticate(self.editor)
        response = self.client.post(
            '/third_side/media', {'file': image()}, format='multipart'
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['url'], f"{HOST}/{response.data['key']}")

    def test_reads_use_the_media_host(self):
        self.client.force_authenticate(self.editor)
        doc = self.client.get(f'/third_side/categories/{self.category.pk}/doc').data
        self.assertEqual(doc['image_url'], f'{HOST}/{KEY}')
        self.assertEqual(doc['hero_image_url'], f'{HOST}/{KEY}')
        self.client.force_authenticate(None)
        groups = str(self.client.get('/third_side/nav-groups?lang=en').data)
        self.assertIn(f'{HOST}/{KEY}', groups)
        self.assertNotIn('/media/third_side', groups)
