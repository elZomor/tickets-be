"""Read-side serializers shaped for the Third Side frontend (?lang=ar|en|ro)."""

from rest_framework import serializers

from third_side.i18n import LOCALES, clean_locale, localize
from third_side.models import Article, Category, Critic, NavGroup, Tag
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
    critic_name = serializers.CharField(source='critic.name', read_only=True)
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
