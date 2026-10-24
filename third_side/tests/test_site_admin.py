from django.core.cache import cache
from rest_framework.test import APITestCase

from third_side.models import (
    AboutPage,
    ActivityLog,
    Article,
    Category,
    Critic,
    NavGroup,
    SiteSettings,
    ThirdSideUser,
)


class _EditorTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = ThirdSideUser.objects.create_user(
            'e@example.com', 'pw', is_superuser=True
        )
        cls.reader = ThirdSideUser.objects.create_user('r@example.com', 'pw')

    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.client.force_authenticate(self.editor)


class NavSectionTests(_EditorTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.group = NavGroup.objects.create(
            slug='visual',
            label={'ar': 'فنون', 'en': 'Visual'},
            url_slug={'ar': 'فنون', 'en': 'visual'},
        )
        cls.category = Category.objects.create(
            name='Cinema',
            slug='cinema',
            group=cls.group,
            name_i18n={'en': 'Cinema'},
            url_slug={'en': 'cinema'},
        )

    def test_create_group_and_category(self):
        response = self.client.post(
            '/third_side/nav-groups',
            {
                'slug': 'stage',
                'order': 3,
                'label': {'ar': 'مسرح', 'en': 'Stage', 'ro': ''},
                'url_slug': {'en': 'the stage'},
                'image_url': '/mock/stage.jpg',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['url_slug'], {'en': 'the-stage'})
        self.assertEqual(response.data['label'], {'ar': 'مسرح', 'en': 'Stage'})

        response = self.client.post(
            '/third_side/categories',
            {
                'slug': 'dance',
                'name_i18n': {'ar': 'رقص', 'en': 'Dance'},
                'group': 'stage',
                'url_slug': {'en': 'dance'},
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        category = Category.objects.get(slug='dance')
        self.assertEqual((category.name, category.group.slug), ('Dance', 'stage'))
        # No position given: last overall, and last in its group.
        self.assertEqual(NavGroup.objects.get(slug='stage').order, 3)
        self.assertEqual(category.order, self.category.order + 1)
        self.assertEqual(category.group_order, 1)
        # The public, localized read reflects it.
        groups = self.client.get('/third_side/nav-groups?lang=en').data['results']
        stage = next(g for g in groups if g['slug'] == 'stage')
        self.assertEqual(stage['categories'], ['dance'])
        self.assertEqual(
            set(ActivityLog.objects.values_list('object_type', flat=True)),
            {'nav_group', 'category'},
        )

    def test_doc_returns_every_locale_and_slug_is_fixed(self):
        doc = self.client.get(f'/third_side/categories/{self.category.pk}/doc').data
        self.assertEqual(doc['name_i18n'], {'en': 'Cinema'})
        self.assertEqual(doc['group'], 'visual')
        response = self.client.patch(
            f'/third_side/categories/{self.category.pk}',
            {'slug': 'film', 'name_i18n': {'en': 'Film'}, 'show_in_nav': False},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.category.refresh_from_db()
        self.assertEqual(self.category.slug, 'cinema')
        self.assertEqual(self.category.name, 'Film')
        self.assertFalse(self.category.show_in_nav)

    def test_long_signed_upload_urls_are_accepted(self):
        # A signed S3 URL easily passes 300 characters; only the key is kept.
        signed = (
            'https://bucket.s3.amazonaws.com/third_side/media/'
            + 'a' * 120
            + '.jpg?X-Amz-Signature='
            + 'f' * 400
        )
        response = self.client.patch(
            f'/third_side/categories/{self.category.pk}',
            {'image_url': signed, 'hero_image_url': signed},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.category.refresh_from_db()
        key = 'third_side/media/' + 'a' * 120 + '.jpg'
        self.assertEqual(self.category.image_url, key)
        self.assertEqual(self.category.hero_image_url, key)
        response = self.client.patch(
            f'/third_side/nav-groups/{self.group.pk}', {'image_url': signed}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.group.refresh_from_db()
        self.assertEqual(self.group.image_url, key)
        # The column's limit still applies to what is saved.
        response = self.client.patch(
            f'/third_side/categories/{self.category.pk}',
            {'image_url': 'third_side/media/' + 'a' * 300 + '.jpg'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('image_url', response.data)

    def test_url_segments_must_be_unique_across_groups_and_categories(self):
        response = self.client.patch(
            f'/third_side/categories/{self.category.pk}',
            {'url_slug': {'en': 'visual'}},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('url_slug', response.data)
        response = self.client.patch(
            f'/third_side/categories/{self.category.pk}',
            {'url_slug': {'en': 'a/b'}},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_category_with_articles_cannot_be_deleted(self):
        Article.objects.create(
            title='t', slug='t', category=self.category, critic=Critic.objects.create()
        )
        response = self.client.delete(f'/third_side/categories/{self.category.pk}')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_moving_a_category_puts_it_last_in_its_new_group(self):
        other = NavGroup.objects.create(slug='written', label={'en': 'Written'})
        Category.objects.create(
            name='Poetry', slug='poetry', group=other, group_order=4
        )
        response = self.client.patch(
            f'/third_side/categories/{self.category.pk}',
            {'group': 'written'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.category.refresh_from_db()
        self.assertEqual(self.category.group_order, 5)

    def test_deleting_a_group_keeps_its_categories(self):
        response = self.client.delete(f'/third_side/nav-groups/{self.group.pk}')
        self.assertEqual(response.status_code, 204)
        self.category.refresh_from_db()
        self.assertIsNone(self.category.group)

    def test_readers_cannot_write_or_read_docs(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(
            self.client.get(f'/third_side/nav-groups/{self.group.pk}/doc').status_code,
            403,
        )
        response = self.client.patch(
            f'/third_side/nav-groups/{self.group.pk}', {'order': 9}, format='json'
        )
        self.assertEqual(response.status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/third_side/nav-groups').status_code, 200)


ABOUT = {
    'hero': {
        'title': {'ar': 'من نحن', 'en': 'About us'},
        'image': 'https://cdn.example.com/media/third_side/media/hero.jpg',
    },
    'team': {'members': [{'name': {'en': 'Sara'}, 'image': '/mock/sara.jpg'}]},
}


class AboutAdminTests(_EditorTestCase):
    def test_save_and_read_back(self):
        response = self.client.put(
            '/third_side/about/doc', {'content': ABOUT}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        stored = AboutPage.load().content
        # Uploaded images are kept by storage key; site paths stay as they are.
        self.assertEqual(stored['hero']['image'], 'third_side/media/hero.jpg')
        self.assertEqual(stored['team']['members'][0]['image'], '/mock/sara.jpg')

        self.client.force_authenticate(None)
        page = self.client.get('/third_side/about?lang=en').data
        self.assertEqual(page['hero']['title'], 'About us')
        self.assertTrue(page['hero']['image'].endswith('third_side/media/hero.jpg'))
        self.assertEqual(ActivityLog.objects.get().object_type, 'about')

    def test_editor_only(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get('/third_side/about/doc').status_code, 403)
        response = self.client.put(
            '/third_side/about/doc', {'content': ABOUT}, format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_content_must_be_an_object(self):
        response = self.client.put(
            '/third_side/about/doc', {'content': [1, 2]}, format='json'
        )
        self.assertEqual(response.status_code, 400)


FOOTER = {
    'contact': {
        'email': 'hi@example.com',
        'phone': '+20 100',
        'address': {'en': 'Cairo', 'ar': 'القاهرة'},
    },
    'social': [{'network': 'facebook', 'url': 'https://facebook.com/x'}],
    'sponsors': [
        {'id': 4, 'name': {'en': 'Old'}, 'url': 'https://old.example.com'},
        {'name': {'en': 'New'}, 'url': ''},
    ],
}


class FooterAdminTests(_EditorTestCase):
    def test_save_keeps_the_hero_and_numbers_new_sponsors(self):
        SiteSettings.objects.create(hero={'image': '/mock/hero.jpg'})
        response = self.client.put('/third_side/footer', FOOTER, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([s['id'] for s in response.data['sponsors']], [4, 5])
        site = SiteSettings.load()
        self.assertEqual(site.hero, {'image': '/mock/hero.jpg'})
        self.assertEqual(site.contact['address']['ar'], 'القاهرة')

        self.client.force_authenticate(None)
        home = self.client.get('/third_side/home?lang=ar').data['site']
        self.assertEqual(home['contact']['address'], 'القاهرة')
        self.assertEqual(home['social'], FOOTER['social'])
        self.assertEqual(home['sponsors'][1]['name'], 'New')

    def test_validation(self):
        bad = {**FOOTER, 'social': [{'network': 'myspace', 'url': 'https://x.y'}]}
        self.assertEqual(
            self.client.put('/third_side/footer', bad, format='json').status_code, 400
        )
        twice = {**FOOTER, 'social': FOOTER['social'] * 2}
        self.assertEqual(
            self.client.put('/third_side/footer', twice, format='json').status_code,
            400,
        )
        bad = {**FOOTER, 'contact': {**FOOTER['contact'], 'email': 'nope'}}
        self.assertEqual(
            self.client.put('/third_side/footer', bad, format='json').status_code, 400
        )

    def test_editor_only(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get('/third_side/footer').status_code, 403)
