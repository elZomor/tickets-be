from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from third_side.models import (
    Article,
    Category,
    Critic,
    Festival,
    Follow,
    NavGroup,
    Notification,
    NotificationPreference,
    ExpoPushDevice,
    PushSubscription,
    SavedArticle,
    ThirdSideUser,
)
from third_side.models.Article import ArticleStatus
from third_side.models.Notification import NotificationType

User = ThirdSideUser
BASE = '/third_side'


class LibraryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = NavGroup.objects.create(slug='g', label={'en': 'Group'})
        cls.category = Category.objects.create(
            name='C', slug='c', name_i18n={'en': 'Cat'}, group=cls.group
        )
        cls.critic = Critic.objects.create(name='K', name_i18n={'en': 'Kay'})
        cls.festival = Festival.objects.create(
            slug='f',
            name_i18n={'en': 'Fest'},
            starts_on=timezone.now().date(),
            ends_on=timezone.now().date(),
        )
        cls.user = User.objects.create_user('u@example.com', 'pw-12345678')
        cls.other = User.objects.create_user('o@example.com', 'pw-12345678')
        cls.live = Article.objects.create(
            title='Live',
            slug='live',
            category=cls.category,
            critic=cls.critic,
            status=ArticleStatus.PUBLISHED,
        )
        cls.draft = Article.objects.create(
            title='Draft',
            slug='draft',
            category=cls.category,
            critic=cls.critic,
            status=ArticleStatus.DRAFT,
        )

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.user)

    def test_anonymous_is_refused(self):
        self.client.force_authenticate(None)
        for path in (
            'saved-articles',
            'saved-articles/ids',
            'follows',
            'notifications',
        ):
            self.assertEqual(self.client.get(f'{BASE}/{path}').status_code, 401, path)

    def test_save_is_idempotent_and_listed(self):
        url = f'{BASE}/saved-articles/{self.live.pk}'
        self.assertEqual(self.client.put(url).status_code, 201)
        self.assertEqual(self.client.put(url).status_code, 200)
        self.assertEqual(SavedArticle.objects.count(), 1)
        ids = self.client.get(f'{BASE}/saved-articles/ids').json()
        self.assertEqual(ids, {'ids': [self.live.pk]})
        listing = self.client.get(f'{BASE}/saved-articles?lang=en').json()
        self.assertEqual([a['id'] for a in listing['results']], [self.live.pk])
        self.assertEqual(listing['results'][0]['path'], '/en/g/c/live')
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(SavedArticle.objects.count(), 0)

    def test_cannot_save_unpublished_or_unknown(self):
        self.assertEqual(
            self.client.put(f'{BASE}/saved-articles/{self.draft.pk}').status_code, 404
        )
        self.assertEqual(
            self.client.put(f'{BASE}/saved-articles/99999').status_code, 404
        )

    def test_saved_are_private_and_hidden_ones_drop_out(self):
        SavedArticle.objects.create(user=self.other, article=self.live)
        self.assertEqual(
            self.client.get(f'{BASE}/saved-articles').json()['results'], []
        )
        SavedArticle.objects.create(user=self.user, article=self.live)
        self.live.is_hidden = True
        self.live.save()
        self.assertEqual(
            self.client.get(f'{BASE}/saved-articles').json()['results'], []
        )

    def test_follow_each_target_type(self):
        for kind, target in [
            ('critic', self.critic),
            ('category', self.category),
            ('navgroup', self.group),
            ('festival', self.festival),
        ]:
            url = f'{BASE}/follows/{kind}/{target.pk}'
            self.assertEqual(self.client.put(url).status_code, 201, kind)
            self.assertEqual(self.client.put(url).status_code, 200, kind)
        listing = self.client.get(f'{BASE}/follows?lang=en').json()
        self.assertEqual(
            {(f['target_type'], f['name']) for f in listing},
            {
                ('critic', 'Kay'),
                ('category', 'Cat'),
                ('navgroup', 'Group'),
                ('festival', 'Fest'),
            },
        )
        url = f'{BASE}/follows/critic/{self.critic.pk}'
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(Follow.objects.filter(user=self.user).count(), 3)

    def test_follow_by_slug(self):
        response = self.client.put(f'{BASE}/follows/navgroup/g')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['target_id'], self.group.pk)
        self.assertEqual(self.client.put(f'{BASE}/follows/category/c').status_code, 201)
        self.assertEqual(self.client.put(f'{BASE}/follows/critic/kay').status_code, 404)
        slugs = {f['slug'] for f in self.client.get(f'{BASE}/follows').json()}
        self.assertEqual(slugs, {'g', 'c'})
        self.assertEqual(
            self.client.delete(f'{BASE}/follows/navgroup/g').status_code, 204
        )
        self.assertEqual(Follow.objects.count(), 1)

    def test_follow_validates_target(self):
        self.assertEqual(
            self.client.put(f'{BASE}/follows/critic/99999').status_code, 404
        )
        self.assertEqual(self.client.put(f'{BASE}/follows/bogus/1').status_code, 404)


class InboxTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('u@example.com', 'pw-12345678')
        cls.other = User.objects.create_user('o@example.com', 'pw-12345678')

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.user)
        self.mine = [
            Notification.objects.create(
                recipient=self.user,
                type=NotificationType.PROFILE_UPDATED,
                dedupe_key=str(index),
            )
            for index in range(3)
        ]
        self.theirs = Notification.objects.create(
            recipient=self.other,
            type=NotificationType.PROFILE_UPDATED,
            dedupe_key='x',
        )

    def test_list_shows_only_own(self):
        data = self.client.get(f'{BASE}/notifications').json()
        self.assertEqual(data['count'], 3)
        self.assertFalse(any(row['read'] for row in data['results']))

    def test_unread_count_and_mark_read(self):
        url = f'{BASE}/notifications'
        self.assertEqual(self.client.get(f'{url}/unread-count').json(), {'count': 3})
        self.assertEqual(
            self.client.post(f'{url}/{self.mine[0].pk}/read').status_code, 200
        )
        self.assertEqual(self.client.get(f'{url}/unread-count').json(), {'count': 2})
        self.assertEqual(self.client.get(f'{url}?unread=1').json()['count'], 2)
        self.assertEqual(self.client.post(f'{url}/read-all').status_code, 204)
        self.assertEqual(self.client.get(f'{url}/unread-count').json(), {'count': 0})
        self.theirs.refresh_from_db()
        self.assertIsNone(self.theirs.read_at)

    def test_cannot_touch_anothers(self):
        url = f'{BASE}/notifications/{self.theirs.pk}'
        self.assertEqual(self.client.post(f'{url}/read').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertEqual(
            self.client.delete(f'{BASE}/notifications/{self.mine[0].pk}').status_code,
            204,
        )

    def test_preferences_default_on_and_update(self):
        url = f'{BASE}/notification-preferences'
        self.assertTrue(self.client.get(url).json()['activity'])
        response = self.client.put(url, {'activity': False}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NotificationPreference.objects.get(user=self.user).activity)
        self.assertTrue(response.json()['status'])

    def test_push_subscription_register_move_and_remove(self):
        url = f'{BASE}/push/subscriptions'
        body = {
            'endpoint': 'https://push.example/abc',
            'keys': {'p256dh': 'k', 'auth': 'a'},
        }
        self.assertEqual(self.client.post(url, body, format='json').status_code, 201)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(url, body, format='json').status_code, 201)
        subscription = PushSubscription.objects.get()
        self.assertEqual(subscription.user, self.other)
        self.client.force_authenticate(self.user)
        self.client.delete(url, {'endpoint': body['endpoint']}, format='json')
        self.assertEqual(PushSubscription.objects.count(), 1)
        self.client.force_authenticate(self.other)
        self.client.delete(url, {'endpoint': body['endpoint']}, format='json')
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_expo_device_register_move_and_remove(self):
        url = f'{BASE}/push/expo-devices'
        body = {'token': 'ExponentPushToken[abc]', 'platform': 'android'}
        self.assertEqual(self.client.post(url, body, format='json').status_code, 201)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(url, body, format='json').status_code, 201)
        self.assertEqual(ExpoPushDevice.objects.get().user, self.other)
        self.client.force_authenticate(self.user)
        self.client.delete(url, {'token': body['token']}, format='json')
        self.assertEqual(ExpoPushDevice.objects.count(), 1)
        self.client.force_authenticate(self.other)
        self.client.delete(url, {'token': body['token']}, format='json')
        self.assertEqual(ExpoPushDevice.objects.count(), 0)

    def test_expo_device_rejects_other_tokens(self):
        response = self.client.post(
            f'{BASE}/push/expo-devices', {'token': 'abc'}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_expo_device_needs_login(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            f'{BASE}/push/expo-devices',
            {'token': 'ExponentPushToken[abc]'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_push_endpoint_must_be_https(self):
        body = {
            'endpoint': 'http://push.example/abc',
            'keys': {'p256dh': 'k', 'auth': 'a'},
        }
        response = self.client.post(f'{BASE}/push/subscriptions', body, format='json')
        self.assertEqual(response.status_code, 400)
