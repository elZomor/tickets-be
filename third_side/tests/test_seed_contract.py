"""Seed from the frontend mock JSON, then check the API serves the same data."""

import json
import unittest
from pathlib import Path

from django.core.management import call_command
from rest_framework.test import APITestCase

MOCK_DIR = Path(__file__).resolve().parents[4] / 'third_side_frontend/app/lib/mock'


@unittest.skipUnless(MOCK_DIR.is_dir(), 'frontend mock directory not available')
class SeedContractTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_third_side', mock_dir=str(MOCK_DIR), verbosity=0)
        cls.home = json.loads((MOCK_DIR / 'home.json').read_text(encoding='utf-8'))
        cls.pages = json.loads(
            (MOCK_DIR / 'category-pages.json').read_text(encoding='utf-8')
        )

    def test_seed_is_idempotent(self):
        call_command('seed_third_side', mock_dir=str(MOCK_DIR), verbosity=0)
        self.assertEqual(
            self.client.get('/third_side/articles?page_size=100').data['count'],
            len(self._all_slugs()),
        )

    def _all_slugs(self):
        slugs = {a['slug']['en'] for a in self.home['latestArticles']}
        for page in self.pages.values():
            slugs.add(page['featured']['slug']['en'])
            slugs.update(a['slug']['en'] for a in page['articles'])
        return slugs

    def test_home_matches_mock(self):
        for lang in ('ar', 'en', 'ro'):
            data = self.client.get(f'/third_side/home?lang={lang}').data
            hero = self.home['hero']
            self.assertEqual(data['hero']['title'], hero['title'][lang])
            self.assertEqual(data['hero']['cta_url'], hero['ctaUrl'][lang])
            self.assertEqual(
                data['site']['contact']['address'],
                self.home['site']['contact']['address'][lang],
            )
            self.assertEqual(
                [c['slug'] for c in data['categories']],
                [c['slug'] for c in sorted(self.home['categories'], key=lambda c: c['order'])],
            )
            for api, mock in zip(
                data['nav_groups'], self.home['navGroups'], strict=True
            ):
                self.assertEqual(api['url_slug'], mock['urlSlug'][lang])
                self.assertEqual(api['categories'], mock['categories'])
            self.assertEqual(len(data['latest_articles']), 6)

    def test_category_pages_match_mock(self):
        languages = json.loads(
            (MOCK_DIR / 'article-languages.json').read_text(encoding='utf-8')
        )
        for slug, page in self.pages.items():
            data = self.client.get(f'/third_side/category-pages/{slug}?lang=en').data
            shown = data['featured']['content_locale']
            self.assertEqual(data['featured']['slug'], page['featured']['slug'][shown])
            self.assertEqual(data['category']['hero_image'], page['heroImage'])
            self.assertEqual(data['category']['description'], page['description']['en'])
            listed = self.client.get(
                f'/third_side/articles?category={slug}&page_size=100&lang=en'
            ).data['results']
            expected = {a['slug']['en'] for a in page['articles']} | {
                page['featured']['slug']['en']
            }
            # The BE lists every article of the category; the mock page curates a subset.
            self.assertTrue(all(a['category_slug'] == slug for a in listed))
            raws = {a['slug']['en']: a for a in page['articles']}
            raws[page['featured']['slug']['en']] = page['featured']
            for key, raw in raws.items():
                original = languages['bySlug'].get(key, languages['default'])['original']
                found = self.client.get(
                    f"/third_side/articles/by-slug/{raw['slug'][original]}?lang=en"
                )
                self.assertEqual(found.status_code, 200, key)
                self.assertIn(found.data['id'], {a['id'] for a in listed}, key)

    def test_article_languages_match_mock(self):
        languages = json.loads(
            (MOCK_DIR / 'article-languages.json').read_text(encoding='utf-8')
        )
        for key, entry in languages['bySlug'].items():
            data = self.client.get(f'/third_side/articles/by-slug/{key}?lang=en')
            if data.status_code == 404:
                continue  # article is not part of the mock pool
            langs = data.data['languages']
            self.assertEqual(langs['original'], entry['original'], key)
            self.assertEqual(set(langs['missing']), set(entry.get('missing', [])), key)
            self.assertEqual(
                {x['locale'] for x in langs['available'] if x['ai']},
                set(entry['ai']) - set(entry.get('missing', [])),
                key,
            )
