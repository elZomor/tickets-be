import io
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from django.utils import timezone
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from third_side.i18n import slug_from_title
from third_side.models import Article, Category, Critic, Media, Tag, ThirdSideUser
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
            'editor@example.com', 'pw', is_superuser=True
        )
        cls.reader = ThirdSideUser.objects.create_user(
            'reader@example.com', 'pw', email_verified=True
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

    def test_same_title_gets_a_numbered_slug(self):
        self.client.force_authenticate(self.editor)
        self.client.post('/third_side/articles', self.body(), format='json')
        response = self.client.post('/third_side/articles', self.body(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['slug'], 'hello-2')
        article = Article.objects.get(pk=response.data['id'])
        self.assertEqual(article.translations.get(locale='ar').slug, 'مرحبا-2')

    def test_slug_follows_the_title_not_the_client(self):
        self.client.force_authenticate(self.editor)
        body = self.body()
        body['doc']['slug'] = {'en': 'something-else'}
        created = self.client.post('/third_side/articles', body, format='json')
        self.assertEqual(created.data['slug'], 'hello')
        body['doc']['title']['en'] = 'Hello, again! (2026)'
        response = self.client.patch(
            f"/third_side/articles/{created.data['id']}", body, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        article = Article.objects.get(pk=created.data['id'])
        self.assertEqual(article.slug, 'hello-again-2026')
        self.assertEqual(article.translations.get(locale='en').slug, 'hello-again-2026')

    def test_title_without_letters_is_rejected(self):
        self.client.force_authenticate(self.editor)
        body = self.body()
        body['doc'] = {'title': {'en': '؟! ...'}}
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
            'editor@example.com', 'pw', is_superuser=True
        )
        cls.reader = ThirdSideUser.objects.create_user(
            'reader@example.com', 'pw', email_verified=True
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

    def test_anonymous_cannot_upload(self):
        self.assertIn(self.upload().status_code, (401, 403))

    def test_readers_upload_for_their_submissions(self):
        self.client.force_authenticate(self.reader)
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Media.objects.get().uploaded_by, self.reader)
        Media.objects.get().file.delete(save=False)


class PublishingAndEditorTests(APITestCase):
    """Cover, editor assignment, publishing and scheduling on the editor API."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Cinema', slug='cinema')
        cls.critic = Critic.objects.create(name='Writer')
        cls.editor = ThirdSideUser.objects.create_user(
            'editor@example.com', 'pw', name='Ed', is_superuser=True
        )
        cls.reader = ThirdSideUser.objects.create_user(
            'reader@example.com', 'pw', email_verified=True
        )

    def body(self, **extra):
        return {
            'category': self.category.pk,
            'critic': self.critic.pk,
            'doc': {
                'title': {'en': 'Hello'},
                'slug': {'en': 'hello'},
                'content': {'en': lexical('hi')},
                'isOriginalLanguage': {'en': True},
            },
            **extra,
        }

    def create(self, **extra):
        self.client.force_authenticate(self.editor)
        response = self.client.post(
            '/third_side/articles', self.body(**extra), format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        return Article.objects.get(pk=response.data['id'])

    def test_cover_and_editor_round_trip(self):
        article = self.create(
            cover_url='http://x/' + 'a' * 600 + '.png', editor=self.editor.pk
        )
        self.assertEqual(article.editor, self.editor)
        doc = self.client.get(f'/third_side/articles/{article.pk}/doc').data
        self.assertEqual(doc['editor'], self.editor.pk)
        self.assertEqual(doc['cover'], article.cover_url)

    def test_editor_must_be_an_editor_user(self):
        self.client.force_authenticate(self.editor)
        response = self.client.post(
            '/third_side/articles', self.body(editor=self.reader.pk), format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_editor_can_be_unassigned_inline(self):
        article = self.create(editor=self.editor.pk)
        response = self.client.patch(
            f'/third_side/articles/{article.pk}', {'editor': None}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        article.refresh_from_db()
        self.assertIsNone(article.editor)

    def test_editors_list_and_filter(self):
        article = self.create(editor=self.editor.pk)
        self.create_other = Article.objects.create(
            title='o', slug='o', category=self.category, critic=self.critic
        )
        listed = self.client.get('/third_side/editors').data
        self.assertEqual(listed, [{'id': self.editor.pk, 'name': 'Ed'}])
        rows = self.client.get(f'/third_side/articles?editor={self.editor.pk}').data
        self.assertEqual([r['id'] for r in rows['results']], [article.pk])
        self.assertEqual(rows['results'][0]['editor_name'], 'Ed')
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get('/third_side/editors').status_code, 403)

    def test_public_never_sees_the_editor(self):
        article = self.create(editor=self.editor.pk, status=ArticleStatus.PUBLISHED)
        self.client.force_authenticate(None)
        data = self.client.get(f'/third_side/articles/{article.pk}').data
        self.assertIsNone(data['editor'])
        self.assertIsNone(data['editor_name'])

    def test_publishing_stamps_the_time(self):
        article = self.create(status=ArticleStatus.PUBLISHED)
        self.assertIsNotNone(article.published_at)

    def test_scheduled_needs_a_future_time(self):
        self.client.force_authenticate(self.editor)
        for extra in (
            {},
            {'published_at': (timezone.now() - timedelta(hours=1)).isoformat()},
        ):
            response = self.client.post(
                '/third_side/articles',
                self.body(status=ArticleStatus.SCHEDULED, **extra),
                format='json',
            )
            self.assertEqual(response.status_code, 400)

    def test_scheduled_goes_live_when_due(self):
        when = timezone.now() + timedelta(hours=1)
        article = self.create(
            status=ArticleStatus.SCHEDULED, published_at=when.isoformat()
        )
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(f'/third_side/articles/{article.pk}').status_code, 404
        )
        Article.objects.filter(pk=article.pk).update(
            published_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(
            self.client.get(f'/third_side/articles/{article.pk}').status_code, 200
        )
        self.client.force_authenticate(self.editor)
        self.client.get('/third_side/articles')
        article.refresh_from_db()
        self.assertEqual(article.status, ArticleStatus.PUBLISHED)


class StoredKeyTests(PublishingAndEditorTests):
    """Uploaded images are stored by key, not by their (possibly signed) URL."""

    def signed(self, key='third_side/media/a.png'):
        return f'https://bucket.s3.amazonaws.com/{key}?X-Amz-Signature=' + 'x' * 800

    def test_cover_is_stored_as_a_key(self):
        article = self.create(cover_url=self.signed())
        self.assertEqual(article.cover_url, 'third_side/media/a.png')

    def test_external_cover_is_kept(self):
        article = self.create(cover_url='https://cdn.example.com/c.jpg')
        self.assertEqual(article.cover_url, 'https://cdn.example.com/c.jpg')

    def test_body_images_keep_the_key_and_read_back_a_url(self):
        content = {
            'root': {
                'type': 'root',
                'children': [
                    {'type': 'upload', 'value': {'id': 1, 'url': self.signed()}}
                ],
            }
        }
        body = self.body()
        body['doc']['content'] = {'en': content}
        self.client.force_authenticate(self.editor)
        created = self.client.post('/third_side/articles', body, format='json')
        article = Article.objects.get(pk=created.data['id'])
        stored = article.translations.get(locale='en').content
        self.assertEqual(
            stored['root']['children'][0]['value']['url'], 'third_side/media/a.png'
        )
        doc = self.client.get(f'/third_side/articles/{article.pk}/doc').data
        url = doc['content']['en']['root']['children'][0]['value']['url']
        self.assertTrue(url.endswith('/media/third_side/media/a.png'), url)


class SlugFromTitleTests(SimpleTestCase):
    def test_keeps_letters_and_digits_and_hyphenates_words(self):
        cases = {
            'Hello, World! (2026)': 'hello-world-2026',
            'هل هذا لير؟': 'هل-هذا-لير',
            'مَرْحَبَاً ـــ بالعالم، يا صديقي': 'مرحبا-بالعالم-يا-صديقي',
            'ما-بعد_الكولونيالية: قراءة': 'ما-بعد-الكولونيالية-قراءة',
            '  ؟؟؟  ': '',
        }
        for title, slug in cases.items():
            self.assertEqual(slug_from_title(title), slug, title)


class ArticleSeoTests(APITestCase):
    """SEO fields the editor saves: per-language title/description, tags, indexing."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Cinema', slug='cinema')
        cls.critic = Critic.objects.create(name='Writer')
        cls.editor = ThirdSideUser.objects.create_user(
            'editor@example.com', 'pw', is_superuser=True
        )
        Tag.objects.create(slug='drama', name={'en': 'Drama'})

    def body(self):
        return {
            'category': self.category.pk,
            'critic': self.critic.pk,
            'status': ArticleStatus.DRAFT,
            'doc': {
                'title': {'en': 'Hello', 'ar': 'مرحبا'},
                'slug': {'en': 'hello', 'ar': 'مرحبا'},
                'content': {'en': lexical('hi'), 'ar': lexical('اهلا')},
                'isOriginalLanguage': {'en': True},
            },
        }

    def seo_body(self):
        body = self.body()
        body['doc']['seoTitle'] = {'en': ' Search title ', 'ar': 'عنوان البحث'}
        body['doc']['metaDescription'] = {'en': 'A description'}
        body['noindex'] = True
        body['canonical_url'] = 'https://example.com/original'
        body['tags'] = ['drama']
        return body

    def test_seo_round_trips_through_save_doc_and_public_detail(self):
        self.client.force_authenticate(self.editor)
        response = self.client.post('/third_side/articles', self.seo_body(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        article = Article.objects.get(pk=response.data['id'])
        self.assertTrue(article.noindex)
        self.assertEqual(list(article.tags.values_list('slug', flat=True)), ['drama'])
        en = article.translations.get(locale='en')
        self.assertEqual((en.seo_title, en.meta_description), ('Search title', 'A description'))

        doc = self.client.get(f'/third_side/articles/{article.pk}/doc').data
        self.assertEqual(doc['seoTitle']['ar'], 'عنوان البحث')
        self.assertEqual(doc['metaDescription']['en'], 'A description')
        self.assertEqual(doc['tags'], ['drama'])
        self.assertTrue(doc['noindex'])
        self.assertEqual(doc['canonicalUrl'], 'https://example.com/original')

        article.status = ArticleStatus.PUBLISHED
        article.published_at = timezone.now()
        article.save()
        self.client.force_authenticate(None)
        detail = self.client.get('/third_side/articles/by-slug/hello?lang=en').data
        self.assertEqual(detail['seo_title'], 'Search title')
        self.assertEqual(detail['meta_description'], 'A description')
        self.assertTrue(detail['noindex'])
        self.assertEqual(detail['canonical_url'], 'https://example.com/original')

    def test_saving_without_seo_keys_keeps_the_stored_text(self):
        self.client.force_authenticate(self.editor)
        response = self.client.post('/third_side/articles', self.seo_body(), format='json')
        pk = response.data['id']
        response = self.client.patch(f'/third_side/articles/{pk}', self.body(), format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            Article.objects.get(pk=pk).translations.get(locale='en').seo_title, 'Search title'
        )

    def test_unknown_tag_and_bad_canonical_are_rejected(self):
        self.client.force_authenticate(self.editor)
        body = self.seo_body()
        body['tags'] = ['missing']
        response = self.client.post('/third_side/articles', body, format='json')
        self.assertEqual(response.status_code, 400)
        body['tags'] = []
        body['canonical_url'] = 'not a url'
        response = self.client.post('/third_side/articles', body, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('canonical_url', response.data)


class PublishedArticleLockTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Cinema', slug='cinema')
        cls.critic = Critic.objects.create(name='Writer')
        cls.editor = ThirdSideUser.objects.create_user(
            'editor@example.com', 'pw', is_superuser=True
        )

    def setUp(self):
        self.client.force_authenticate(self.editor)

    def body(self, status):
        return {
            'category': self.category.pk,
            'critic': self.critic.pk,
            'status': status,
            'doc': {
                'title': {'en': 'Hello'},
                'content': {'en': lexical('hi')},
                'isOriginalLanguage': {'en': True},
            },
        }

    def publish(self):
        response = self.client.post(
            '/third_side/articles', self.body(ArticleStatus.PUBLISHED), format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['id']

    def test_publishing_itself_is_allowed_then_it_is_locked(self):
        pk = self.publish()
        self.assertEqual(Article.objects.get(pk=pk).status, ArticleStatus.PUBLISHED)
        for method in (self.client.put, self.client.patch):
            response = method(
                f'/third_side/articles/{pk}',
                self.body(ArticleStatus.PUBLISHED),
                format='json',
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn('locked', str(response.data['detail']))

    def test_a_published_article_cannot_change_state_or_text_or_be_deleted(self):
        pk = self.publish()
        url = f'/third_side/articles/{pk}'
        for patch in (
            {'status': ArticleStatus.DRAFT},
            {'editor': self.editor.pk},
            {'doc': {'title': {'en': 'Changed'}}},
        ):
            self.assertEqual(
                self.client.patch(url, patch, format='json').status_code, 400, patch
            )
        self.assertEqual(self.client.delete(url).status_code, 400)
        article = Article.objects.get(pk=pk)
        self.assertEqual(article.status, ArticleStatus.PUBLISHED)
        self.assertEqual(article.title, 'Hello')
        self.assertEqual(article.translations.get(locale='en').title, 'Hello')

    def test_other_states_stay_editable_and_deletable(self):
        created = self.client.post(
            '/third_side/articles', self.body(ArticleStatus.DRAFT), format='json'
        )
        url = f"/third_side/articles/{created.data['id']}"
        response = self.client.patch(
            url, self.body(ArticleStatus.SUBMITTED), format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_a_scheduled_article_that_came_due_is_locked_once_published(self):
        created = self.client.post(
            '/third_side/articles',
            {
                **self.body(ArticleStatus.SCHEDULED),
                'published_at': (timezone.now() + timedelta(hours=1)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.data)
        pk = created.data['id']
        Article.objects.filter(pk=pk).update(
            published_at=timezone.now() - timedelta(minutes=1)
        )
        response = self.client.patch(
            f'/third_side/articles/{pk}', {'editor': self.editor.pk}, format='json'
        )
        self.assertEqual(response.status_code, 400)
