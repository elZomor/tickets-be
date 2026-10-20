import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase

from third_side.models import Article, Category, Critic, Media, Role, ThirdSideUser
from third_side.models.Article import ArticleStatus


def lexical(text):
    return {'root': {'type': 'root', 'children': [{'type': 'text', 'text': text}]}}


def png_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (20, 10), 'red').save(buffer, 'PNG')
    return buffer.getvalue()


class AdminArticleTests(APITestCase):
    """The admin editor's save/read path: POST/PATCH /articles with a `doc`."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Cinema', slug='cinema')
        cls.critic = Critic.objects.create(name='Writer')
        cls.editor = ThirdSideUser.objects.create_user(
            'editor@example.com', 'pw', role=Role.EDITOR
        )
        cls.reader = ThirdSideUser.objects.create_user(
            'reader@example.com', 'pw', role=Role.READER
        )

    def body(self, **extra):
        return {
            'category': self.category.pk,
            'critic': self.critic.pk,
            'status': ArticleStatus.DRAFT,
            'doc': {
                'title': {'en': 'Hello', 'ar': 'مرحبا'},
                'slug': {'en': 'hello', 'ar': 'مرحبا'},
                'content': {'en': lexical('hi'), 'ar': lexical('اهلا')},
                'isOriginalLanguage': {'en': True},
                'aiGenerated': {'ar': True},
            },
            **extra,
        }

    def test_create_saves_translations_and_follows_original_language(self):
        self.client.force_authenticate(self.editor)
        response = self.client.post('/third_side/articles', self.body(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        article = Article.objects.get(pk=response.data['id'])
        self.assertEqual((article.title, article.slug), ('Hello', 'hello'))
        self.assertEqual(article.original_language, 'en')
        self.assertFalse(article.via_website)
        rows = {t.locale: t for t in article.translations.all()}
        self.assertEqual(set(rows), {'en', 'ar'})
        self.assertTrue(rows['ar'].is_ai_generated)

    def test_update_changes_one_language(self):
        self.client.force_authenticate(self.editor)
        created = self.client.post('/third_side/articles', self.body(), format='json')
        body = self.body(status=ArticleStatus.SUBMITTED)
        body['doc']['title']['en'] = 'Hello again'
        response = self.client.patch(
            f"/third_side/articles/{created.data['id']}", body, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        article = Article.objects.get(pk=created.data['id'])
        self.assertEqual(article.status, ArticleStatus.SUBMITTED)
        self.assertEqual(article.translations.get(locale='en').title, 'Hello again')

    def test_doc_endpoint_returns_every_language(self):
        self.client.force_authenticate(self.editor)
        created = self.client.post('/third_side/articles', self.body(), format='json')
        data = self.client.get(f"/third_side/articles/{created.data['id']}/doc").data
        self.assertEqual(data['title'], {'en': 'Hello', 'ar': 'مرحبا'})
        self.assertEqual(data['isOriginalLanguage'], {'en': True, 'ar': False})
        self.assertEqual(data['aiGenerated'], {'en': False, 'ar': True})
        self.assertEqual(data['critic'], self.critic.pk)

    def test_duplicate_slug_is_a_validation_error(self):
        self.client.force_authenticate(self.editor)
        self.client.post('/third_side/articles', self.body(), format='json')
        response = self.client.post('/third_side/articles', self.body(), format='json')
        self.assertEqual(response.status_code, 400)

    def test_doc_without_any_title_and_slug_is_rejected(self):
        self.client.force_authenticate(self.editor)
        body = self.body()
        body['doc'] = {'title': {'en': 'Only a title'}, 'slug': {}}
        response = self.client.post('/third_side/articles', body, format='json')
        self.assertEqual(response.status_code, 400)

    def test_readers_cannot_save_or_read_docs(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(
            self.client.post(
                '/third_side/articles', self.body(), format='json'
            ).status_code,
            403,
        )
        article = Article.objects.create(
            title='t', slug='t', category=self.category, critic=self.critic
        )
        self.assertEqual(
            self.client.get(f'/third_side/articles/{article.pk}/doc').status_code, 403
        )


class MediaUploadTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = ThirdSideUser.objects.create_user(
            'editor@example.com', 'pw', role=Role.EDITOR
        )
        cls.reader = ThirdSideUser.objects.create_user(
            'reader@example.com', 'pw', role=Role.READER
        )

    def upload(self, name='a.png', data=None, content_type='image/png'):
        file = SimpleUploadedFile(name, data or png_bytes(), content_type=content_type)
        return self.client.post('/third_side/media', {'file': file}, format='multipart')

    def test_editor_uploads_an_image(self):
        self.client.force_authenticate(self.editor)
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['width'], response.data['height']), (20, 10))
        self.assertTrue(response.data['url'].startswith('http'))
        self.assertEqual(Media.objects.count(), 1)
        Media.objects.get().file.delete(save=False)

    def test_rejects_non_images(self):
        self.client.force_authenticate(self.editor)
        response = self.upload('a.txt', b'hello', 'text/plain')
        self.assertEqual(response.status_code, 400)
        response = self.upload('a.png', b'not really a png', 'image/png')
        self.assertEqual(response.status_code, 400)

    def test_readers_and_anonymous_cannot_upload(self):
        self.assertIn(self.upload().status_code, (401, 403))
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.upload().status_code, 403)
