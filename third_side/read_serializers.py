"""Read-side serializers shaped for the Third Side frontend (?lang=ar|en|ro)."""

from rest_framework import serializers

from third_side.i18n import LOCALES, clean_locale, localize
from third_side.models import (
    Article,
    Category,
    Critic,
    Festival,
    FestivalPost,
    NavGroup,
    Tag,
)
from third_side.models.FestivalPost import FestivalPostType
from third_side.services.festivals import article_path, shown_translation
from third_side.services.translations import (
    languages_of,
    pick_locale,
    translation_map,
)


def _lang(serializer):
    request = serializer.context.get('request')
    return clean_locale(request.query_params.get('lang') if request else None)


def _media_url(serializer, file_field, fallback_url):
    if file_field:
        request = serializer.context.get('request')
        url = file_field.url
        return request.build_absolute_uri(url) if request else url
    return fallback_url or None


class NavGroupSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    url_slug = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()

    class Meta:
        model = NavGroup
        fields = [
            'id',
            'slug',
            'order',
            'url_slug',
            'label',
            'tagline',
            'description',
            'image',
            'categories',
        ]

    def get_image(self, obj) -> str | None:
        return _media_url(self, obj.image, obj.image_url)

    def get_url_slug(self, obj) -> str:
        return localize(obj.url_slug, _lang(self), obj.slug)

    def get_label(self, obj) -> str:
        return localize(obj.label, _lang(self), obj.slug)

    def get_tagline(self, obj) -> str:
        return localize(obj.tagline, _lang(self))

    def get_description(self, obj) -> str:
        return localize(obj.description, _lang(self))

    def get_categories(self, obj) -> list[str]:
        ordered = sorted(obj.categories.all(), key=lambda c: (c.group_order, c.id))
        return [c.slug for c in ordered]


class CategoryReadSerializer(serializers.ModelSerializer):
    group = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    url_slugs = serializers.SerializerMethodField()
    url_slug = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    hero_image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id',
            'slug',
            'order',
            'group',
            'show_in_nav',
            'featured',
            'name',
            'url_slug',
            'url_slugs',
            'tagline',
            'description',
            'image',
            'hero_image',
        ]

    def get_name(self, obj) -> str:
        return localize(obj.name_i18n, _lang(self), obj.name)

    def get_url_slug(self, obj) -> str:
        return localize(obj.url_slug, _lang(self), obj.slug)

    def get_url_slugs(self, obj) -> dict:
        return {
            code: localize(obj.url_slug, code, obj.slug) for code in ('ar', 'en', 'ro')
        }

    def get_tagline(self, obj) -> str:
        return localize(obj.tagline, _lang(self))

    def get_description(self, obj) -> str:
        return localize(obj.description, _lang(self))

    def get_image(self, obj) -> str | None:
        return _media_url(self, obj.image, obj.image_url)

    def get_hero_image(self, obj) -> str | None:
        return obj.hero_image_url or _media_url(self, obj.image, obj.image_url)


class TagSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    url_slug = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['slug', 'url_slug', 'name']

    def get_name(self, obj) -> str:
        return localize(obj.name, _lang(self), obj.slug)

    def get_url_slug(self, obj) -> str:
        return localize(obj.url_slug, _lang(self), obj.slug)


class ArticleReadSerializer(serializers.ModelSerializer):
    """Article card: legacy fields plus localized title/slug and the new metadata."""

    title = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    slugs = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    content_locale = serializers.SerializerMethodField()
    languages = serializers.SerializerMethodField()
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    category_name = serializers.SerializerMethodField()
    critic_name = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    rating = serializers.SerializerMethodField()
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'slug',
            'slugs',
            'excerpt',
            'content',
            'category',
            'category_slug',
            'category_name',
            'critic',
            'critic_name',
            'cover',
            'tags',
            'status',
            'published_at',
            'created_at',
            'via_website',
            'created_by',
            'is_hidden',
            'is_featured',
            'share_count',
            'read_count',
            'original_language',
            'content_locale',
            'languages',
            'rating',
        ]

    def _translations(self, obj):
        cache = self.context.setdefault('_translations', {})
        if obj.pk not in cache:
            cache[obj.pk] = translation_map(obj)
        return cache[obj.pk]

    def _shown(self, obj):
        translations = self._translations(obj)
        locale = pick_locale(translations, _lang(self), obj.original_language)
        return locale, translations[locale]

    def get_title(self, obj) -> str:
        return self._shown(obj)[1]['title']

    def get_slug(self, obj) -> str:
        return self._shown(obj)[1]['slug']

    def get_slugs(self, obj) -> dict:
        return {k: v['slug'] for k, v in self._translations(obj).items()}

    def get_excerpt(self, obj) -> str:
        return self._shown(obj)[1]['excerpt']

    def get_content_locale(self, obj) -> str:
        return self._shown(obj)[0]

    def get_languages(self, obj) -> dict:
        return languages_of(self._translations(obj), obj.original_language)

    def get_critic_name(self, obj) -> str:
        return localize(obj.critic.name_i18n, _lang(self), obj.critic.name)

    def get_category_name(self, obj) -> str:
        return localize(obj.category.name_i18n, _lang(self), obj.category.name)

    def get_cover(self, obj) -> str | None:
        return _media_url(self, obj.cover, obj.cover_url)

    def get_rating(self, obj) -> dict:
        average = getattr(obj, 'rating_avg', None)
        return {
            'average': round(average, 2) if average else 0,
            'count': getattr(obj, 'rating_count', 0),
        }


class ArticleDetailSerializer(ArticleReadSerializer):
    body = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()

    class Meta(ArticleReadSerializer.Meta):
        fields = ArticleReadSerializer.Meta.fields + ['body', 'meta_description']

    def get_body(self, obj):
        return self._shown(obj)[1]['content']

    def get_meta_description(self, obj) -> str:
        data = self._shown(obj)[1]
        return data['meta_description'] or data['excerpt']


class CriticReadSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    slugs = serializers.SerializerMethodField()
    main_category = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    article_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Critic
        fields = [
            'id',
            'name',
            'bio',
            'photo',
            'slug',
            'slugs',
            'main_category',
            'article_count',
        ]

    def get_name(self, obj) -> str:
        return localize(obj.name_i18n, _lang(self), obj.name)

    def get_bio(self, obj) -> str:
        return localize(obj.bio_i18n, _lang(self), obj.bio or '')

    def get_photo(self, obj) -> str | None:
        return _media_url(self, obj.photo, obj.photo_url)

    def get_slug(self, obj) -> str:
        return localize(obj.slug_i18n, _lang(self), str(obj.pk))

    def get_slugs(self, obj) -> dict:
        return {code: localize(obj.slug_i18n, code, str(obj.pk)) for code in LOCALES}


class FestivalReadSerializer(serializers.ModelSerializer):
    slug = serializers.SerializerMethodField()
    slugs = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    posts_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Festival
        fields = [
            'id',
            'slug',
            'slugs',
            'name',
            'description',
            'location',
            'cover',
            'starts_on',
            'ends_on',
            'posts_count',
        ]

    def get_slug(self, obj) -> str:
        return localize(obj.slug_i18n, _lang(self), obj.slug)

    def get_slugs(self, obj) -> dict:
        return {code: localize(obj.slug_i18n, code, obj.slug) for code in LOCALES}

    def get_name(self, obj) -> str:
        return localize(obj.name_i18n, _lang(self), obj.slug)

    def get_description(self, obj) -> str:
        return localize(obj.description_i18n, _lang(self))

    def get_location(self, obj) -> str:
        return localize(obj.location_i18n, _lang(self))

    def get_cover(self, obj) -> str | None:
        return _media_url(self, obj.cover, obj.cover_url)


class FestivalPostReadSerializer(serializers.ModelSerializer):
    """A feed post. Only the keys that apply to its `type` are present."""

    class Meta:
        model = FestivalPost
        fields = ['id', 'type', 'published_at']

    def to_representation(self, obj):
        lang = _lang(self)
        data = super().to_representation(obj)
        festival = obj.festival
        data['is_published'] = obj.is_published
        data['festival'] = {
            'id': festival.id,
            'name': localize(festival.name_i18n, lang, festival.slug),
            'slug': localize(festival.slug_i18n, lang, festival.slug),
        }
        kind = obj.type
        shown = []
        if kind == FestivalPostType.TITLED_TEXT:
            data['title'] = self._text(obj.title_i18n, lang, shown)
        if kind in (FestivalPostType.TEXT, FestivalPostType.TITLED_TEXT):
            data['body'] = self._text(obj.body_i18n, lang, shown)
        if kind in (FestivalPostType.IMAGE_CAPTION, FestivalPostType.VIDEO_CAPTION):
            data['caption'] = self._text(obj.caption_i18n, lang, shown)
        if kind in (FestivalPostType.IMAGE, FestivalPostType.IMAGE_CAPTION):
            data['media'] = [
                {
                    'url': _media_url(self, item.image, item.image_url),
                    'alt': localize(item.alt_i18n, lang),
                }
                for item in obj.media.all()
            ]
        if kind in (FestivalPostType.VIDEO, FestivalPostType.VIDEO_CAPTION):
            video_file = obj.video_file
            data['video'] = {
                'kind': obj.video_kind,
                'url': _media_url(self, video_file, obj.video_url),
                'poster': _media_url(self, obj.poster, obj.poster_url),
            }
        if kind == FestivalPostType.ARTICLE and obj.article:
            article = obj.article
            translation = shown_translation(article, lang)
            data['article'] = {
                'title': translation.title if translation else article.title,
                'excerpt': translation.excerpt if translation else '',
                'cover': _media_url(self, article.cover, article.cover_url),
                'path': article_path(article, lang, translation),
            }
            shown.append(translation.locale if translation else lang)
        data['locales'] = self._locales(obj)
        # Text shown in another language than requested (no translation yet).
        content_locale = next((code for code in shown if code != lang), None)
        if content_locale:
            data['content_locale'] = content_locale
        return data

    @staticmethod
    def _locales(obj):
        """Languages the post has text in (an article post: its article's)."""
        if obj.type == FestivalPostType.ARTICLE and obj.article:
            have = {t.locale for t in obj.article.translations.all()}
        else:
            maps = (obj.title_i18n, obj.body_i18n, obj.caption_i18n)
            have = {
                code
                for values in maps
                if isinstance(values, dict)
                for code in values
                if values[code]
            }
        return [code for code in LOCALES if code in have]

    @staticmethod
    def _text(values, lang, shown):
        """`lang`'s text, else the default locale's, noting which locale it is."""
        if not isinstance(values, dict):
            return ''
        for code in (lang, 'ar', *LOCALES):
            if values.get(code):
                shown.append(code)
                return values[code]
        return ''
