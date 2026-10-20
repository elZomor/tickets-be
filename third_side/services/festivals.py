"""Festival feed helpers."""

from third_side.i18n import localize
from third_side.services.translations import pick_locale


def shown_translation(article, lang):
    """The ArticleTranslation `article` shows for `lang` (None without any)."""
    rows = {t.locale: t for t in article.translations.all()}
    if not rows:
        return None
    return rows[pick_locale(rows, lang, article.original_language)]


def article_path(article, lang, translation):
    """Frontend address of `article` in `lang`: /<lang>/<group>/<category>/<slug>,
    without the group segment for an ungrouped category."""
    category = article.category
    parts = [lang]
    if category.group_id:
        parts.append(localize(category.group.url_slug, lang, category.group.slug))
    parts.append(localize(category.url_slug, lang, category.slug))
    parts.append(translation.slug if translation else article.slug)
    return '/' + '/'.join(parts)
