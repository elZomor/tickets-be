import shutil
import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from third_side.models import ActivityLog, Article, Category, Critic
from third_side.models import ThirdSideUser
from third_side.tests.test_admin_articles import png_bytes

MEDIA_ROOT = tempfile.mkdtemp()
BODY = 'x' * 120


def image(name='a.png'):
    return SimpleUploadedFile(name, png_bytes(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class _MediaTestCase(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()  # throttle counters live in the cache


class SubmissionImageTests(_MediaTestCase):
    @classmethod
    def setUpTestData(cls):
        Category.objects.create(name='Cinema', slug='cinema')
        cls.reader = ThirdSideUser.objects.create_user('r@example.com', 'pw', email_verified=True)
        cls.other = ThirdSideUser.objects.create_user('o@example.com', 'pw', email_verified=True)
        cls.editor = ThirdSideUser.objects.create_user(
            'e@example.com', 'pw', is_superuser=True
        )

    def upload(self):
        response = self.client.post(
            '/third_side/media', {'file': image()}, format='multipart'
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['id']

    def submit(self, images):
        return self.client.post(
            '/third_side/submissions',
            {
                'category_slug': 'cinema',
                'title': 'With pictures',
                'language': 'en',
                'content': BODY,
                'images': images,
            },
            format='json',
        )

    def test_reader_upload_is_not_in_the_activity_log(self):
        self.client.force_authenticate(self.reader)
        self.upload()
        self.assertFalse(ActivityLog.objects.exists())

    def test_images_are_attached_and_appended_to_the_editor_doc(self):
        self.client.force_authenticate(self.reader)
        first, second = self.upload(), self.upload()
        response = self.submit([first, second])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data['images']), 2)
        article = Article.objects.get()
        self.assertEqual(
            sorted(article.submitted_media.values_list('pk', flat=True)),
            [first, second],
        )

        self.client.force_authenticate(self.editor)
        doc = self.client.get(f'/third_side/articles/{article.pk}/doc').data
        children = doc['content']['en']['root']['children']
        self.assertEqual(
            [node['type'] for node in children], ['paragraph', 'upload', 'upload']
        )
        self.assertEqual(children[1]['value']['id'], first)
        self.assertTrue(children[1]['value']['url'].startswith('http'))

    def test_cannot_attach_someone_elses_image(self):
        self.client.force_authenticate(self.other)
        theirs = self.upload()
        self.client.force_authenticate(self.reader)
        response = self.submit([theirs])
        self.assertEqual(response.status_code, 400)
        self.assertIn('images', response.data)

    def test_at_most_ten_images(self):
        self.client.force_authenticate(self.reader)
        response = self.submit(list(range(1, 12)))
        self.assertEqual(response.status_code, 400)

    def test_submission_without_images_still_works(self):
        self.client.force_authenticate(self.reader)
        response = self.submit([])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['images'], [])


class AvatarTests(_MediaTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reader = ThirdSideUser.objects.create_user('r@example.com', 'pw', email_verified=True)

    def post(self, file):
        return self.client.post(
            '/third_side/profile/me/avatar', {'file': file}, format='multipart'
        )

    def test_requires_login(self):
        self.assertEqual(self.post(image()).status_code, 401)

    def test_set_replace_and_remove(self):
        self.client.force_authenticate(self.reader)
        self.assertIsNone(self.client.get('/third_side/profile/me').data['avatar'])

        response = self.post(image('me.png'))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['avatar'].startswith('http'))
        first = ThirdSideUser.objects.get(pk=self.reader.pk).avatar.name
        self.assertTrue(first.startswith('third_side/avatars/'))

        with self.captureOnCommitCallbacks(execute=True):
            self.post(image('again.png'))
        user = ThirdSideUser.objects.get(pk=self.reader.pk)
        self.assertNotEqual(user.avatar.name, first)
        self.assertFalse(user.avatar.storage.exists(first))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete('/third_side/profile/me/avatar')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['avatar'])
        self.assertFalse(ThirdSideUser.objects.get(pk=self.reader.pk).avatar)

    def test_rejects_non_images(self):
        self.client.force_authenticate(self.reader)
        bad = SimpleUploadedFile('a.png', b'nope', content_type='image/png')
        self.assertEqual(self.post(bad).status_code, 400)

    def test_writer_page_falls_back_to_the_avatar(self):
        critic = Critic.objects.create(name='Reader', user=self.reader)
        self.client.force_authenticate(self.reader)
        self.post(image())
        self.client.force_authenticate(None)
        data = self.client.get(f'/third_side/critics/{critic.pk}').data
        self.assertIn('third_side/avatars/', data['photo'])
