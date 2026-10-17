import logging

from django.db import IntegrityError, transaction

from third_side.i18n import LOCALES
from third_side.models import ArticleTranslation
from third_side.services.payload_sync import text_to_lexical

logger = logging.getLogger(__name__)


def sync_translations(article, doc):
    """Upsert ArticleTranslation rows from a Payload doc (locale: 'all' maps)."""
    titles = doc.get('title') or {}
    slugs = doc.get('slug') or {}
    contents = doc.get('content') or {}
    if not all(isinstance(m, dict) for m in (titles, slugs, contents)):
        return
    for locale in LOCALES:
        title, slug = titles.get(locale), slugs.get(locale)
        if not title or not slug:
            continue
        try:
            with transaction.atomic():
                ArticleTranslation.objects.update_or_create(
                    article=article,
                    locale=locale,
                    defaults={
                        'title': title,
                        'slug': slug,
                        'content': contents.get(locale),
                    },
                )
        except IntegrityError:
            logger.warning(
                'Translation slug %r/%s already used; skipped for article %s',
                slug,
                locale,
                article.pk,
            )


def translation_map(article):
    """{locale: view} for every language the article exists in.

    The base Article row stands in for the original language when it has no
    translation row of its own (articles created Django-side before sync).
    """
    rows = {t.locale: t for t in article.translations.all()}
    result = {
        locale: {
            'title': t.title,
            'slug': t.slug,
            'excerpt': t.excerpt,
            'meta_description': t.meta_description,
            'content': t.content,
            'is_ai_generated': t.is_ai_generated,
        }
        for locale, t in rows.items()
    }
    original = article.original_language
    if original not in result:
        result[original] = {
            'title': article.title,
            'slug': article.slug,
            'excerpt': '',
            'meta_description': '',
            'content': text_to_lexical(article.content) if article.content else None,
            'is_ai_generated': False,
        }
    return result


def pick_locale(translations, lang, original):
    """The locale whose content is shown for `lang`: lang, else the original."""
    if lang in translations:
        return lang
    if original in translations:
        return original
    return next(iter(translations))


def languages_of(translations, original):
    return {
        'original': original,
        'available': [
            {'locale': locale, 'ai': locale != original and data['is_ai_generated']}
            for locale, data in sorted(
                translations.items(), key=lambda item: item[0] != original
            )
        ],
        'missing': [locale for locale in LOCALES if locale not in translations],
    }
