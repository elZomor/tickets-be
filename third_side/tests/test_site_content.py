from datetime import date, timedelta

from rest_framework.test import APITestCase

from third_side.models import AboutPage, Ad, Article, Category, Critic
from third_side.models.Article import ArticleStatus

LOC = {'ar': 'عربي', 'en': 'English', 'ro': 'Romana'}


def ad(name, **kwargs):
    today = date.today()
    defaults = dict(
        type='sponsor',
        name=name,
        url='/about',
        internal=True,
        starts_at=today - timedelta(days=1),
        ends_at=today + timedelta(days=1),
        weight=1,
        alt=LOC,
        images={k: {'tall': f'/{name}-{k}-t.png', 'rect': f'/{name}-{k}-r.png'} for k in LOC},
    )
    defaults.update(kwargs)
    return Ad.objects.create(**defaults)


class WritersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name='Cinema', slug='cinema')
        cls.critic = Critic.objects.create(
            name='Sara',
            name_i18n={'ar': 'سارة', 'en': 'Sara', 'ro': 'Sara'},
            bio_i18n={'ar': 'نبذة', 'en': 'Bio'},
            slug_i18n={'ar': 'سارة', 'en': 'sara', 'ro': 'sara'},
            main_category=category,
        )
        Article.objects.create(
            title='a', slug='a', category=category, critic=cls.critic,
            status=ArticleStatus.PUBLISHED,
        )
        Article.objects.create(title='b', slug='b', category=category, critic=cls.critic)

    def test_list_is_localized_with_published_count(self):
        data = self.client.get('/third_side/critics?lang=ar').data['results'][0]
        self.assertEqual(data['name'], 'سارة')
        self.assertEqual(data['bio'], 'نبذة')
        self.assertEqual(data['slugs']['en'], 'sara')
        self.assertEqual(data['main_category'], 'cinema')
        self.assertEqual(data['article_count'], 1)

    def test_bio_falls_back_to_available_locale(self):
        data = self.client.get('/third_side/critics?lang=ro').data['results'][0]
        self.assertEqual(data['bio'], 'نبذة')  # default locale before any other

    def test_by_slug_any_locale(self):
        for slug in ('sara', 'سارة'):
            response = self.client.get(f'/third_side/critics/by-slug/{slug}?lang=en')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['id'], self.critic.pk)
        self.assertEqual(self.client.get('/third_side/critics/by-slug/nope').status_code, 404)

    def test_articles_of_critic(self):
        data = self.client.get(f'/third_side/articles?critic={self.critic.pk}').data
        self.assertEqual(data['count'], 1)


class AboutTests(APITestCase):
    def test_404_until_configured_then_localized(self):
        self.assertEqual(self.client.get('/third_side/about').status_code, 404)
        AboutPage.objects.create(
            content={
                'title': LOC,
                'sections': [{'lead': LOC, 'body': [LOC]}],
                'values': [{'id': 'v', 'title': LOC, 'text': LOC}],
                'hero_image': '/x.jpg',
            }
        )
        data = self.client.get('/third_side/about?lang=en').data
        self.assertEqual(data['title'], 'English')
        self.assertEqual(data['sections'][0]['body'], ['English'])
        self.assertEqual(data['values'][0]['id'], 'v')
        self.assertEqual(data['hero_image'], '/x.jpg')


class AdsTests(APITestCase):
    def pick(self, query=''):
        return self.client.get(f'/third_side/ads/pick?size=rect&lang=en{query}')

    def test_no_active_ads_is_204(self):
        self.assertEqual(self.pick().status_code, 204)

    def test_only_active_in_window_and_locale(self):
        ad('expired', ends_at=date.today() - timedelta(days=1))
        ad('future', starts_at=date.today() + timedelta(days=1))
        ad('off', is_active=False)
        ad('ar-only', locales=['ar'])
        self.assertEqual(self.pick().status_code, 204)
        live = ad('live')
        data = self.pick().data
        self.assertEqual(data['id'], live.pk)
        self.assertEqual(data['image'], '/live-en-r.png')
        self.assertEqual(data['alt'], 'English')

    def test_exclude_avoids_repeat_unless_only_one(self):
        first, second = ad('one', locales=['en']), ad('two', locales=['en'])
        for _ in range(10):
            self.assertEqual(self.pick(f'&exclude={first.pk}').data['id'], second.pk)
        only = ad('solo', locales=['ro'])
        response = self.client.get(f'/third_side/ads/pick?size=tall&lang=ro&exclude={only.pk}')
        self.assertEqual(response.data['id'], only.pk)

    def test_weight_zero_never_picked(self):
        ad('zero', weight=0)
        self.assertEqual(self.pick().status_code, 204)

    def test_size_required(self):
        self.assertEqual(self.client.get('/third_side/ads/pick').status_code, 400)

    def test_impression_and_click_counters(self):
        live = ad('live')
        for kind in ('impression', 'impression', 'click'):
            self.assertEqual(
                self.client.post(f'/third_side/ads/{live.pk}/{kind}').status_code, 204
            )
        live.refresh_from_db()
        self.assertEqual((live.impressions, live.clicks), (2, 1))
        self.assertEqual(self.client.post('/third_side/ads/999/click').status_code, 404)
