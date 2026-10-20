"""Locale helpers for the Third Side content (ar is the default and RTL)."""

import re
import unicodedata

LOCALES = ('ar', 'en', 'ro')
DEFAULT_LOCALE = 'ar'
LOCALE_CHOICES = [(code, code) for code in LOCALES]


def default_locales():
    return list(LOCALES)


def clean_locale(value, default=DEFAULT_LOCALE):
    return value if value in LOCALES else default


def localize(values, lang, fallback=''):
    """Pick `lang` from a {locale: text} map, then the default locale, then any."""
    if not isinstance(values, dict):
        return fallback
    for code in (lang, DEFAULT_LOCALE):
        if values.get(code):
            return values[code]
    return next((text for text in values.values() if text), fallback)


def localize_tree(value, lang):
    """Collapse every {ar,en,ro} map inside a JSON tree to `lang`'s text."""
    if isinstance(value, dict):
        if value and set(value) <= set(LOCALES):
            return localize(value, lang)
        return {key: localize_tree(item, lang) for key, item in value.items()}
    if isinstance(value, list):
        return [localize_tree(item, lang) for item in value]
    return value


def slugify_name(name):
    """Lower-case, drop punctuation, hyphenate: the frontend's writerSlug rule."""
    return re.sub(r'\s+', '-', re.sub(r'[^\w\s-]', '', name.strip().lower()))


_WORD_BREAKS = re.compile(r'[\s_/\u2013\u2014-]+')


def slug_from_title(title):
    """The article slug for a title: its letters and digits, hyphen-separated.

    Punctuation, Arabic marks (tashkeel, ؟ ، ؛) and tatweel are dropped; spaces,
    hyphens and underscores separate words. Latin is lower-cased, Arabic kept.
    """
    words = []
    for word in _WORD_BREAKS.split(title or ''):
        kept = ''.join(
            ch for ch in word if unicodedata.category(ch)[0] in 'LN' and ch != '\u0640'
        )
        if kept:
            words.append(kept.lower())
    return '-'.join(words)[:200].strip('-')


def unique_slug(base, taken):
    """`base`, or `base-2`, `base-3`... the first one `taken(slug)` says is free."""
    slug, n = base, 2
    while taken(slug):
        slug = f'{base}-{n}'
        n += 1
    return slug
