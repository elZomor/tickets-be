"""Locale helpers for the Third Side content (ar is the default and RTL)."""

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
