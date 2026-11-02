from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from third_side.models import NavGroup, ThirdSideUser


@override_settings(THIRD_SIDE_READ_CACHE_TTL=60)
class AnonymousReadCacheTests(APITestCase):
    def setUp(self):
        cache.clear()
        NavGroup.objects.create(slug='visual', url_slug={'en': 'visual'})

    def test_anonymous_get_is_cached_and_marked_public(self):
        first = self.client.get('/third_side/nav-groups?lang=en')
        self.assertEqual(first['X-Cache'], 'MISS')
        self.assertIn('s-maxage=60', first['Cache-Control'])
        NavGroup.objects.create(slug='perf', url_slug={'en': 'perf'})
        second = self.client.get('/third_side/nav-groups?lang=en')
        self.assertEqual(second['X-Cache'], 'HIT')
        self.assertEqual(second.content, first.content)

    def test_locale_is_part_of_the_key(self):
        self.client.get('/third_side/nav-groups?lang=en')
        self.assertEqual(self.client.get('/third_side/nav-groups?lang=ar')['X-Cache'], 'MISS')

    def test_authenticated_requests_bypass_the_cache(self):
        user = ThirdSideUser.objects.create_user('u@example.com', 'pw')
        self.client.force_authenticate(user)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer x')
        response = self.client.get('/third_side/nav-groups?lang=en')
        self.assertNotIn('X-Cache', response)

    def test_random_ad_pick_is_never_cached(self):
        response = self.client.get('/third_side/ads/pick?lang=en&size=slim')
        self.assertNotIn('X-Cache', response)

    def test_unknown_or_free_text_params_bypass_the_cache(self):
        for qs in ('?lang=en&search=abc', '?lang=en&zzz=1'):
            self.assertNotIn('X-Cache', self.client.get('/third_side/articles' + qs))

    def test_param_order_does_not_split_the_key(self):
        self.client.get('/third_side/nav-groups?lang=en&page=1')
        self.assertEqual(
            self.client.get('/third_side/nav-groups?page=1&lang=en')['X-Cache'], 'HIT'
        )
