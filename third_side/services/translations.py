import logging

from django.db import IntegrityError, transaction

from third_side.i18n import LOCALES
from third_side.models import ArticleTranslation
from third_side.services.media_urls import content_to_keys, content_to_urls

logger = logging.getLogger(__name__)


def _text_node(text):
    return {
        'mode': 'normal',
        'text': text,
        'type': 'text',
        'style': '',
        'detail': 0,
        'format': 0,
        'version': 1,
    }


def _paragraph_node(text):
    return {
        'type': 'paragraph',
        'format': '',
        'indent': 0,
        'version': 1,
        'children': [_text_node(text)] if text else [],
        'direction': None,
        'textStyle': '',
        'textFormat': 0,
    }


def text_to_lexical(text):
    """Wrap a plain-text Article.content into Lexical rich-text JSON.

    A single paragraph holding the whole string, matching the shape the
    admin editor itself produces (this only needs the plain-paragraph subset).
    """
    return {
        'root': {
            'type': 'root',
            'format': '',
            'indent': 0,
            'version': 1,
            'children': [_paragraph_node(text or '')],
            'direction': None,
        }
    }


def _sync_original_language(article, ticks, titles, slugs):
    """Set Article.original_language from the editor's per-locale tick.

    Exactly one ticked locale wins. With several ticked, keep the current
    original if it is among them, else the first in ar/en/ro order. With none
    ticked (or a doc without the field) the current value stays. A locale with
    no text yet cannot be the original.
    """
    if not isinstance(ticks, dict):
        return
    ticked = [
        locale
        for locale in LOCALES
        if ticks.get(locale) and titles.get(locale) and slugs.get(locale)
    ]
    if not ticked:
        return
    chosen = (
        article.original_language if article.original_language in ticked else ticked[0]
    )
    if chosen != article.original_language:
        article.original_language = chosen
        article.save(update_fields=['original_language'])


def sync_translations(article, doc):
    """Upsert ArticleTranslation rows from an editor doc ({field: {locale: value}} maps)."""
    titles = doc.get('title') or {}
    slugs = doc.get('slug') or {}
    contents = doc.get('content') or {}
    # Per-locale "machine-translated" tick from the editor. A doc without
    # the field leaves the Django-side flag untouched.
    ai_flags = doc.get('aiGenerated')
    if not isinstance(ai_flags, dict):
        ai_flags = {}
    if not all(isinstance(m, dict) for m in (titles, slugs, contents)):
        return
    _sync_original_language(article, doc.get('isOriginalLanguage'), titles, slugs)
    for locale in LOCALES:
        title, slug = titles.get(locale), slugs.get(locale)
        if not title or not slug:
            continue
        defaults = {
            'title': title,
            'slug': slug,
            'content': content_to_keys(contents.get(locale)),
        }
        if locale in ai_flags:
            defaults['is_ai_generated'] = bool(ai_flags[locale])
        # SEO text is only touched when the editor sent it for this language.
        for key, field in (
            ('seoTitle', 'seo_title'),
            ('metaDescription', 'meta_description'),
        ):
            values = doc.get(key)
            if isinstance(values, dict) and locale in values:
                defaults[field] = (values[locale] or '').strip()
        try:
            with transaction.atomic():
                ArticleTranslation.objects.update_or_create(
                    article=article, locale=locale, defaults=defaults
                )
        except IntegrityError:
            logger.warning(
                'Translation slug %r/%s already used; skipped for article %s',
                slug,
                locale,
                article.pk,
            )


def translation_map(article, request=None):
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
            'seo_title': t.seo_title,
            'content': content_to_urls(t.content, request),
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
            'seo_title': '',
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
