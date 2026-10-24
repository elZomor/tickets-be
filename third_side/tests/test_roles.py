from datetime import timedelta

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from third_side.models import Article, Category, Comment, Critic, Report, ThirdSideUser
from third_side.models.Article import ArticleStatus
from third_side.services.roles import ROLES, sync_roles


def lexical(text):
    return {'root': {'type': 'root', 'children': [{'type': 'text', 'text': text}]}}


class RoleTestCase(APITestCase):
    """The staff groups and what each one may do."""

    @classmethod
    def setUpTestData(cls):
        sync_roles()
        cls.category = Category.objects.create(name='Cinema', slug='cinema')
        cls.critic = Critic.objects.create(name='Writer')
        cls.users = {}
        for name in ROLES:
            user = ThirdSideUser.objects.create_user(
                f"{name.lower().replace(' ', '')}@example.com", 'pw'
            )
            user.groups.add(Group.objects.get(name=name))
            cls.users[name] = user
        cls.users['Admin'] = ThirdSideUser.objects.create_user(
            'admin@example.com', 'pw', is_superuser=True
        )
        cls.users['Reader'] = ThirdSideUser.objects.create_user(
            'reader@example.com', 'pw'
        )

    def setUp(self):
        cache.clear()

    def as_(self, role):
        self.client.force_authenticate(self.users[role])

    def article(self, status=ArticleStatus.DRAFT, author=None, slug='a'):
        return Article.objects.create(
            title=slug,
            slug=slug,
            category=self.category,
            critic=self.critic,
            status=status,
            created_by=self.users[author] if author else None,
        )

    def body(self, **extra):
        return {
            'category': self.category.pk,
            'critic': self.critic.pk,
            'status': ArticleStatus.DRAFT,
            'doc': {
                'title': {'en': 'Hello'},
                'slug': {'en': 'hello'},
                'content': {'en': lexical('hi')},
                'isOriginalLanguage': {'en': True},
            },
            **extra,
        }

    def soon(self):
        return (timezone.now() + timedelta(days=1)).isoformat()

    def patch(self, article, **data):
        return self.client.patch(
            f'/third_side/articles/{article.pk}', data, format='json'
        )


class GroupsTests(RoleTestCase):
    def test_every_permission_in_the_table_exists(self):
        self.assertEqual(sync_roles(), {})

    def test_sync_is_idempotent(self):
        sync_roles()
        self.assertEqual(Group.objects.count(), len(ROLES))

    def test_profile_lists_groups_and_permissions(self):
        self.as_('Moderator')
        me = self.client.get('/third_side/profile/me').data
        self.assertEqual(me['groups'], ['Moderator'])
        self.assertIn('change_report', me['permissions'])
        self.assertNotIn('add_article', me['permissions'])
        self.as_('Admin')
        admin = self.client.get('/third_side/profile/me').data
        self.assertIn('change_sitesettings', admin['permissions'])

    def test_a_group_member_does_not_get_more_than_the_group(self):
        self.assertFalse(self.users['Writer'].has_perm('third_side.publish_article'))
        self.assertTrue(self.users['Publisher'].has_perm('third_side.publish_article'))
        self.assertTrue(self.users['Admin'].has_perm('third_side.change_sitesettings'))
        self.assertFalse(self.users['Reader'].has_perm('third_side.add_article'))


class ReaderTests(RoleTestCase):
    def test_a_reader_cannot_write_anything_in_the_admin(self):
        self.as_('Reader')
        article = self.article(author='Reader')
        post = self.client.post
        self.assertEqual(
            post('/third_side/articles', self.body(), format='json').status_code, 403
        )
        self.assertEqual(self.patch(article, status='SUBMITTED').status_code, 403)
        self.assertEqual(
            self.client.get(f'/third_side/articles/{article.pk}/doc').status_code, 403
        )
        self.assertEqual(
            post('/third_side/categories', {}, format='json').status_code, 403
        )
        self.assertEqual(self.client.get('/third_side/reports').status_code, 403)
        self.assertEqual(self.client.get('/third_side/emails').status_code, 403)
        self.assertEqual(self.client.get('/third_side/activity-log').status_code, 403)
        self.assertEqual(self.client.get('/third_side/editors').status_code, 403)

    def test_a_reader_sees_only_live_articles(self):
        self.as_('Reader')
        self.article(author='Reader', slug='mine')
        response = self.client.get('/third_side/articles')
        self.assertEqual(response.data['count'], 0)


class WriterTests(RoleTestCase):
    def setUp(self):
        super().setUp()
        self.as_('Writer')

    def test_creates_a_draft_and_may_submit_it(self):
        response = self.client.post('/third_side/articles', self.body(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        article = Article.objects.get(pk=response.data['id'])
        self.assertEqual(article.created_by, self.users['Writer'])
        self.assertEqual(self.patch(article, status='SUBMITTED').status_code, 200)

    def test_cannot_create_into_a_review_or_publishing_state(self):
        for status in ('UNDER_REVIEW', 'PUBLISHED', 'SCHEDULED'):
            response = self.client.post(
                '/third_side/articles',
                self.body(status=status, published_at=self.soon()),
                format='json',
            )
            self.assertEqual(response.status_code, 403, status)

    def test_edits_own_piece_only_while_it_is_theirs_to_work_on(self):
        for status, expected in (
            (ArticleStatus.DRAFT, 200),
            (ArticleStatus.REJECTED, 200),
            (ArticleStatus.CHANGES_REQUESTED, 200),
            (ArticleStatus.SUBMITTED, 403),
            (ArticleStatus.UNDER_REVIEW, 403),
            (ArticleStatus.READY_FOR_PUBLISHING, 403),
        ):
            article = self.article(status, author='Writer', slug=f'own-{status}')
            self.assertEqual(
                self.patch(article, title='Changed').status_code, expected, status
            )

    def test_cannot_edit_someone_elses_piece(self):
        hidden = self.article(author='Reviewer', slug='hidden')
        self.assertEqual(self.patch(hidden, title='Mine now').status_code, 404)
        live = self.article(ArticleStatus.PUBLISHED, author='Reviewer', slug='live')
        self.assertEqual(self.patch(live, title='Mine now').status_code, 403)

    def test_cannot_publish_or_hand_out_staff_fields(self):
        article = self.article(author='Writer')
        self.assertEqual(self.patch(article, status='PUBLISHED').status_code, 403)
        self.assertEqual(self.patch(article, status='UNDER_REVIEW').status_code, 403)
        self.assertEqual(self.patch(article, is_hidden=True).status_code, 403)
        self.assertEqual(
            self.patch(article, editor=self.users['Reviewer'].pk).status_code, 403
        )
        # Sending a field at the value it already has is not a change.
        self.assertEqual(
            self.patch(article, is_hidden=False, editor=None).status_code, 200
        )

    def test_cannot_delete(self):
        article = self.article(author='Writer')
        response = self.client.delete(f'/third_side/articles/{article.pk}')
        self.assertEqual(response.status_code, 403)

    def test_sees_the_live_articles_and_their_own_pieces(self):
        self.article(ArticleStatus.PUBLISHED, slug='live')
        self.article(ArticleStatus.DRAFT, author='Writer', slug='mine')
        self.article(ArticleStatus.DRAFT, author='Reviewer', slug='theirs')
        response = self.client.get('/third_side/articles')
        slugs = {row['slug'] for row in response.data['results']}
        self.assertEqual(slugs, {'live', 'mine'})

    def test_reads_the_doc_of_their_own_piece_only(self):
        mine = self.article(author='Writer', slug='mine')
        theirs = self.article(author='Reviewer', slug='theirs')
        self.assertEqual(
            self.client.get(f'/third_side/articles/{mine.pk}/doc').status_code, 200
        )
        self.assertIn(
            self.client.get(f'/third_side/articles/{theirs.pk}/doc').status_code,
            (403, 404),
        )

    def test_has_no_say_over_the_site(self):
        for url in ('/third_side/categories', '/third_side/critics', '/third_side/ads'):
            response = self.client.post(url, {}, format='json')
            self.assertEqual(response.status_code, 403, url)
        self.assertEqual(self.client.get('/third_side/reports').status_code, 403)


class ReviewerTests(RoleTestCase):
    def setUp(self):
        super().setUp()
        self.as_('Reviewer')

    def test_moves_a_submission_through_review_and_sends_it_back(self):
        article = self.article(ArticleStatus.SUBMITTED, author='Writer')
        for status in (
            'UNDER_REVIEW',
            'CHANGES_REQUESTED',
            'REJECTED',
            'READY_FOR_EDITING',
        ):
            self.assertEqual(self.patch(article, status=status).status_code, 200)

    def test_cannot_publish_schedule_or_archive(self):
        article = self.article(ArticleStatus.READY_FOR_EDITING, author='Writer')
        for status in ('READY_FOR_PUBLISHING', 'SCHEDULED', 'PUBLISHED', 'ARCHIVED'):
            response = self.patch(article, status=status, published_at=self.soon())
            self.assertEqual(response.status_code, 403, status)

    def test_edits_any_piece_and_sets_the_editor(self):
        article = self.article(ArticleStatus.SUBMITTED, author='Writer')
        response = self.patch(article, editor=self.users['Reviewer'].pk)
        self.assertEqual(response.status_code, 200, response.data)

    def test_sees_unpublished_articles_but_cannot_delete(self):
        article = self.article(ArticleStatus.SUBMITTED, author='Writer')
        self.assertEqual(self.client.get('/third_side/articles').data['count'], 1)
        response = self.client.delete(f'/third_side/articles/{article.pk}')
        self.assertEqual(response.status_code, 403)

    def test_assignable_editors_are_the_reviewers(self):
        names = {row['id'] for row in self.client.get('/third_side/editors').data}
        self.assertEqual(
            names,
            {
                self.users['Reviewer'].pk,
                self.users['Publisher'].pk,
                self.users['Admin'].pk,
            },
        )


class PublisherTests(RoleTestCase):
    def test_publishes_and_deletes(self):
        self.as_('Publisher')
        article = self.article(ArticleStatus.READY_FOR_PUBLISHING, author='Writer')
        self.assertEqual(self.patch(article, status='PUBLISHED').status_code, 200)
        draft = self.article(slug='draft')
        response = self.client.delete(f'/third_side/articles/{draft.pk}')
        self.assertEqual(response.status_code, 204)


class ModeratorTests(RoleTestCase):
    def test_moderates_reports_and_comments_but_not_articles(self):
        self.as_('Moderator')
        article = self.article(ArticleStatus.PUBLISHED, slug='live')
        comment = Comment.objects.create(
            user=self.users['Reader'], article=article, text='hi', is_hidden=True
        )
        report = Report.objects.create(
            reporter=self.users['Reader'],
            content_type=ContentType.objects.get_for_model(Comment),
            object_id=comment.pk,
        )
        self.assertEqual(self.client.get('/third_side/reports').status_code, 200)
        reviewed = self.client.patch(f'/third_side/reports/{report.pk}/review')
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        comment.refresh_from_db()
        self.assertFalse(comment.is_hidden)
        self.assertEqual(self.patch(article, title='x').status_code, 403)
        self.assertEqual(
            self.client.post(
                '/third_side/articles', self.body(), format='json'
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get('/third_side/activity-log').status_code, 403)


class ContentManagerTests(RoleTestCase):
    def test_manages_the_site_structure_but_not_articles(self):
        self.as_('Content Manager')
        created = self.client.post(
            '/third_side/nav-groups',
            {'slug': 'x', 'order': 1, 'name': {'ar': 'س', 'en': 'x', 'ro': 'x'}},
            format='json',
        )
        self.assertNotEqual(created.status_code, 403, created.data)
        self.assertEqual(
            self.client.post(
                '/third_side/articles', self.body(), format='json'
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get('/third_side/footer').status_code, 403)


class MarketingTests(RoleTestCase):
    def test_runs_ads_and_email_only(self):
        self.as_('Marketing')
        self.assertEqual(self.client.get('/third_side/ads').status_code, 200)
        self.assertEqual(self.client.get('/third_side/emails').status_code, 200)
        self.assertEqual(self.client.get('/third_side/reports').status_code, 403)
        self.assertEqual(self.client.get('/third_side/activity-log').status_code, 403)


class SiteAdminTests(RoleTestCase):
    def test_a_superuser_can_do_everything(self):
        self.as_('Admin')
        article = self.article(ArticleStatus.SUBMITTED, author='Writer')
        self.assertEqual(self.patch(article, status='PUBLISHED').status_code, 200)
        self.assertEqual(self.client.get('/third_side/footer').status_code, 200)
        self.assertEqual(self.client.get('/third_side/activity-log').status_code, 200)

    def test_an_inactive_account_holds_nothing(self):
        user = self.users['Admin']
        user.is_active = False
        self.assertFalse(user.has_perm('third_side.add_article'))
