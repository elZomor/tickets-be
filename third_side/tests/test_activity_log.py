import io
import tempfile
from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from third_side.models import (
    ActivityLog,
    Article,
    Category,
    Critic,
    Festival,
    FestivalPost,
    Report,
    Role,
    ThirdSideUser,
)
from third_side.models.Article import ArticleStatus

ARTICLES = '/third_side/articles'
LOG = '/third_side/activity-log'


def lexical(text):
    return {'root': {'type': 'root', 'children': [{'type': 'text', 'text': text}]}}


def png_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (20, 10), 'red').save(buffer, 'PNG')
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ActivityLogTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Cinema', slug='cinema')
        cls.critic = Critic.objects.create(name='Writer')
        cls.editor = ThirdSideUser.objects.create_user(
            'editor@example.com', 'pw', role=Role.EDITOR, name='Ed'
        )
        cls.other = ThirdSideUser.objects.create_user(
            'other@example.com', 'pw', role=Role.EDITOR
        )
        cls.reader = ThirdSideUser.objects.create_user(
            'reader@example.com', 'pw', role=Role.READER
        )
        cls.festival = Festival.objects.create(
            slug='fest',
            name_i18n={'en': 'Fest'},
            starts_on='2026-01-01',
            ends_on='2026-01-05',
        )

    def setUp(self):
        self.client.force_authenticate(self.editor)

    def body(self, **extra):
        return {
            'category': self.category.pk,
            'critic': self.critic.pk,
            'status': ArticleStatus.DRAFT,
            'doc': {
                'title': {'en': 'Hello', 'ar': 'مرحبا'},
                'content': {'en': lexical('hi'), 'ar': lexical('اهلا')},
                'isOriginalLanguage': {'en': True},
            },
            **extra,
        }

    def create_article(self):
        response = self.client.post(ARTICLES, self.body(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['id']

    def test_create_logs_actor_and_the_new_values(self):
        pk = self.create_article()
        row = ActivityLog.objects.get()
        self.assertEqual(
            (row.action, row.object_type, row.object_id, row.object_repr),
            ('create', 'article', pk, 'Hello'),
        )
        self.assertEqual(
            (row.actor, row.actor_name, row.actor_email),
            (self.editor, 'Ed', 'editor@example.com'),
        )
        self.assertEqual(row.changes['status'], {'before': None, 'after': 'DRAFT'})
        self.assertEqual(row.changes['title.ar']['after'], 'مرحبا')
        self.assertEqual(row.changes['content.en']['after'], lexical('hi'))
        self.assertIsNotNone(row.created_at)

    def test_update_logs_only_what_changed(self):
        pk = self.create_article()
        body = self.body(status=ArticleStatus.SUBMITTED)
        body['doc']['content']['en'] = lexical('changed')
        self.client.patch(f'{ARTICLES}/{pk}', body, format='json')
        row = ActivityLog.objects.filter(action='update').get()
        self.assertEqual(
            set(row.changes), {'status', 'content.en'}, 'the Arabic text did not change'
        )
        self.assertEqual(
            row.changes['status'], {'before': 'DRAFT', 'after': 'SUBMITTED'}
        )
        self.assertEqual(row.changes['content.en']['before'], lexical('hi'))
        self.assertEqual(row.changes['content.en']['after'], lexical('changed'))

    def test_title_change_logs_the_slug_that_followed(self):
        pk = self.create_article()
        body = self.body()
        body['doc']['title']['en'] = 'Hello again'
        self.client.patch(f'{ARTICLES}/{pk}', body, format='json')
        row = ActivityLog.objects.filter(action='update').get()
        self.assertEqual(
            row.changes['slug.en'], {'before': 'hello', 'after': 'hello-again'}
        )

    def test_saving_without_changes_logs_nothing(self):
        pk = self.create_article()
        self.client.patch(f'{ARTICLES}/{pk}', self.body(), format='json')
        self.assertEqual(ActivityLog.objects.filter(action='update').count(), 0)

    def test_delete_logs_the_last_values_and_keeps_the_name(self):
        pk = self.create_article()
        self.assertEqual(self.client.delete(f'{ARTICLES}/{pk}').status_code, 204)
        row = ActivityLog.objects.get(action='delete')
        self.assertEqual((row.object_id, row.object_repr), (pk, 'Hello'))
        self.assertEqual(row.changes['title.en'], {'before': 'Hello', 'after': None})
        self.assertFalse(Article.objects.filter(pk=pk).exists())

    def test_festival_post_media_is_compared_by_content_not_row_id(self):
        body = {
            'festival': self.festival.pk,
            'type': 'image',
            'media': [{'image_url': 'third_side/festival-posts/a.png', 'order': 0}],
        }
        created = self.client.post('/third_side/festival-posts', body, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        url = f"/third_side/festival-posts/{created.data['id']}"
        # Same media again: the serializer re-creates the rows, the log must not care.
        when = '2026-02-01T00:00:00Z'
        response = self.client.patch(url, {**body, 'published_at': when}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        row = ActivityLog.objects.get(action='update')
        self.assertEqual(set(row.changes), {'published_at'})

    def test_category_and_critic_writes_are_logged(self):
        self.client.post(
            '/third_side/categories', {'name': 'Dance', 'slug': 'dance'}, format='json'
        )
        self.client.post('/third_side/critics', {'name': 'New'}, format='json')
        kinds = set(ActivityLog.objects.values_list('object_type', flat=True))
        self.assertEqual(kinds, {'category', 'critic'})

    def test_media_upload_is_logged(self):
        file = SimpleUploadedFile('a.png', png_bytes(), content_type='image/png')
        response = self.client.post('/third_side/media', {'file': file})
        self.assertEqual(response.status_code, 201, response.data)
        row = ActivityLog.objects.get(action='upload')
        self.assertEqual(row.object_type, 'media')
        self.assertEqual(row.changes['mime_type']['after'], 'image/png')
        self.assertTrue(row.changes['file']['after'].startswith('third_side/media/'))

    def test_report_review_is_logged(self):
        article = Article.objects.create(
            title='t',
            slug='t',
            category=self.category,
            critic=self.critic,
            is_hidden=True,
        )
        from django.contrib.contenttypes.models import ContentType

        report = Report.objects.create(
            reporter=self.reader,
            content_type=ContentType.objects.get_for_model(Article),
            object_id=article.pk,
        )
        self.client.patch(f'/third_side/reports/{report.pk}/review')
        row = ActivityLog.objects.get(action='review')
        self.assertEqual(
            row.changes['target_is_hidden'], {'before': True, 'after': False}
        )

    def test_failed_save_leaves_no_log_row(self):
        with mock.patch(
            'third_side.views.audit_mixin.audit.record', side_effect=RuntimeError
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(ARTICLES, self.body(), format='json')
        self.assertFalse(Article.objects.exists())
        self.assertFalse(ActivityLog.objects.exists())

    def test_readers_cannot_read_the_log(self):
        self.create_article()
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get(LOG).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(LOG).status_code, 401)

    def test_list_filters_and_detail(self):
        pk = self.create_article()
        self.client.force_authenticate(self.other)
        self.client.post('/third_side/critics', {'name': 'New'}, format='json')
        listing = self.client.get(LOG).data
        self.assertEqual(listing['count'], 2)
        self.assertEqual(listing['results'][0]['object_type'], 'critic')
        self.assertNotIn('changes', listing['results'][0])
        self.assertIn('name', listing['results'][0]['changed_fields'])

        def count(query):
            return self.client.get(f'{LOG}?{query}').data['count']

        self.assertEqual(count(f'actor={self.editor.pk}'), 1)
        self.assertEqual(count('object_type=article'), 1)
        self.assertEqual(count(f'object_type=article&object_id={pk}'), 1)
        self.assertEqual(count('action=delete'), 0)
        self.assertEqual(count('search=hello'), 1)
        self.assertEqual(count('search=other@'), 1)
        self.assertEqual(count('actor=abc'), 0)
        today = timezone.now().date().isoformat()
        self.assertEqual(count(f'date_from={today}&date_to={today}'), 2)
        self.assertEqual(count('date_to=2000-01-01'), 0)

        row_id = listing['results'][1]['id']
        detail = self.client.get(f'{LOG}/{row_id}').data
        self.assertEqual(detail['changes']['title.en']['after'], 'Hello')

    def test_the_log_cannot_be_written_through_the_api(self):
        self.create_article()
        row = ActivityLog.objects.get()
        self.assertEqual(self.client.delete(f'{LOG}/{row.pk}').status_code, 405)
        self.assertEqual(self.client.post(LOG, {}, format='json').status_code, 405)

    def test_actor_snapshot_survives_the_account(self):
        self.create_article()
        self.editor.delete()
        row = ActivityLog.objects.get()
        self.assertIsNone(row.actor)
        self.assertEqual(row.actor_email, 'editor@example.com')


class PurgeActivityLogTests(APITestCase):
    def test_purges_only_rows_older_than_the_limit(self):
        old = ActivityLog.objects.create(
            action='update', object_type='article', changes={'a': 1}
        )
        ActivityLog.objects.create(
            action='update', object_type='article', changes={'a': 1}
        )
        ActivityLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=400)
        )
        call_command('purge_activity_log', '--dry-run', verbosity=0)
        self.assertEqual(ActivityLog.objects.count(), 2)
        call_command('purge_activity_log', verbosity=0)
        self.assertEqual(ActivityLog.objects.count(), 1)
        self.assertFalse(ActivityLog.objects.filter(pk=old.pk).exists())


class FestivalPostSnapshotTests(APITestCase):
    def test_post_snapshot_has_media_list(self):
        from third_side.services import audit

        festival = Festival.objects.create(
            slug='f2',
            name_i18n={'en': 'F'},
            starts_on='2026-01-01',
            ends_on='2026-01-05',
        )
        post = FestivalPost.objects.create(festival=festival, type='text')
        self.assertEqual(audit.snapshot(post)['media'], [])


class TagCreateTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = ThirdSideUser.objects.create_user(
            'editor@example.com', 'pw', role=Role.EDITOR
        )
        cls.reader = ThirdSideUser.objects.create_user(
            'reader@example.com', 'pw', role=Role.READER
        )

    def post(self, name):
        return self.client.post('/third_side/tags', {'name': name}, format='json')

    def test_editor_creates_a_tag_and_it_is_logged(self):
        self.client.force_authenticate(self.editor)
        response = self.post({'ar': 'مسرح الشارع', 'en': 'Street Theatre'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['slug'], 'street-theatre')
        self.assertEqual(response.data['name']['ro'], 'مسرح الشارع')
        self.assertEqual(
            response.data['url_slug'],
            {'ar': 'مسرح-الشارع', 'en': 'street-theatre', 'ro': 'مسرح-الشارع'},
        )
        row = ActivityLog.objects.get()
        self.assertEqual((row.action, row.object_type), ('create', 'tag'))
        self.assertEqual(row.object_repr, 'Street Theatre')

    def test_one_language_is_enough_and_the_slug_follows_it(self):
        self.client.force_authenticate(self.editor)
        response = self.post({'ar': 'نقد'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['slug'], 'نقد')
        self.assertEqual(response.data['name'], {'ar': 'نقد', 'en': 'نقد', 'ro': 'نقد'})

    def test_bad_names_are_rejected(self):
        self.client.force_authenticate(self.editor)
        for bad in ({}, {'ar': '  '}, {'ar': '؟!'}, {'fr': 'x'}, 'text'):
            self.assertEqual(self.post(bad).status_code, 400, bad)

    def test_existing_tag_is_not_created_twice(self):
        self.client.force_authenticate(self.editor)
        self.post({'en': 'Dance'})
        self.assertEqual(self.post({'en': 'dance!'}).status_code, 400)

    def test_only_editors_create_but_anyone_lists(self):
        self.assertEqual(self.post({'en': 'X'}).status_code, 401)
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.post({'en': 'X'}).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/third_side/tags').status_code, 200)
