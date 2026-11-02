from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APITestCase

from third_side.models import Category, NavGroup, ThirdSideUser
from third_side.services.roles import sync_roles


class ComingSoonFlagTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        sync_roles()
        cls.group = NavGroup.objects.create(slug='visual', url_slug={'en': 'visual'})
        cls.category = Category.objects.create(
            name='Cinema', slug='cinema', group=cls.group
        )
        cls.manager = ThirdSideUser.objects.create_user('cm@example.com', 'pw')
        cls.manager.groups.add(Group.objects.get(name='Content Manager'))

    def setUp(self):
        cache.clear()

    def test_defaults_to_off_and_shows_in_the_public_payloads(self):
        categories = self.client.get('/third_side/categories?lang=en').data['results']
        self.assertIs(categories[0]['is_coming_soon'], False)
        groups = self.client.get('/third_side/nav-groups?lang=en').data['results']
        self.assertIs(groups[0]['is_coming_soon'], False)

    def test_a_content_manager_flips_it_on_a_category_and_a_group(self):
        self.client.force_authenticate(self.manager)
        response = self.client.patch(
            f'/third_side/categories/{self.category.pk}',
            {'is_coming_soon': True},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.patch(
            f'/third_side/nav-groups/{self.group.pk}',
            {'is_coming_soon': True},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(None)
        cache.clear()
        categories = self.client.get('/third_side/categories?lang=en').data['results']
        groups = self.client.get('/third_side/nav-groups?lang=en').data['results']
        self.assertIs(categories[0]['is_coming_soon'], True)
        self.assertIs(groups[0]['is_coming_soon'], True)

    def test_a_reader_cannot_flip_it(self):
        reader = ThirdSideUser.objects.create_user('r@example.com', 'pw')
        self.client.force_authenticate(reader)
        response = self.client.patch(
            f'/third_side/categories/{self.category.pk}',
            {'is_coming_soon': True},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
