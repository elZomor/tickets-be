from datetime import date

from rest_framework.test import APITestCase

from hita_arab_festival.models import ArabFestival


class FestivalVisibilityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.visible = ArabFestival.objects.create(
            name='الدورة ٤١',
            description='desc',
            start_date=date(2025, 12, 15),
            end_date=date(2025, 12, 19),
        )
        cls.hidden = ArabFestival.objects.create(
            name='الدورة ٤٢',
            description='desc',
            start_date=date(2026, 12, 15),
            end_date=date(2026, 12, 19),
            is_visible=False,
        )

    def test_list_excludes_hidden_festivals(self):
        response = self.client.get('/hita_arab_festival/festivals')
        self.assertEqual(response.status_code, 200)
        ids = [f['id'] for f in response.data['results']]
        self.assertEqual(ids, [self.visible.id])

    def test_hidden_festival_detail_is_not_found(self):
        response = self.client.get(f'/hita_arab_festival/festivals/{self.hidden.id}')
        self.assertEqual(response.status_code, 404)
