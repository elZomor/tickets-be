"""Editor writes of the site's own content: header sections, About, footer.

Localized fields are {"ar", "en", "ro"} maps. Images come from POST /media and
are stored by key (see services/media_urls); reads turn them back into URLs.
"""

import re

from django.db.models import Max
from rest_framework import serializers

from third_side.i18n import LOCALES
from third_side.models import Category, NavGroup
from third_side.serializers import _clean_text_map
from third_side.services.media_urls import to_key, to_url

SOCIAL_NETWORKS = ('facebook', 'instagram', 'x', 'tiktok', 'youtube')
# Keys inside the About content that hold an image.
IMAGE_KEYS = ('image',)
MAX_ABOUT_BYTES = 200_000


def clean_url_slugs(value, field='url_slug'):
    """{locale: segment}: trimmed, inner spaces as hyphens, no slashes."""
    cleaned = _clean_text_map(value, field)
    for locale, text in cleaned.items():
        segment = re.sub(r'\s+', '-', text)
        if '/' in segment or '?' in segment or '#' in segment:
            raise serializers.ValidationError(
                {field: f'"{text}" cannot be part of an address.'}
            )
        cleaned[locale] = segment
    return cleaned


def check_url_slugs_free(url_slug, instance):
    """Header groups and categories share the first URL segment per locale."""
    taken = []
    for model in (NavGroup, Category):
        rows = model.objects.all()
        if isinstance(instance, model):
            rows = rows.exclude(pk=instance.pk)
        taken += [row.url_slug or {} for row in rows.only('url_slug')]
    for locale, segment in url_slug.items():
        if any(other.get(locale) == segment for other in taken):
            raise serializers.ValidationError(
                {'url_slug': f'"{segment}" ({locale}) is already used.'}
            )


def _next(rows, field):
    return (rows.aggregate(top=Max(field))['top'] or 0) + 1


def _image_out(file_field, url, request):
    if url:
        return to_url(url, request)
    if file_field:
        return request.build_absolute_uri(file_field.url) if request else file_field.url
    return ''


class _SectionWriteSerializer(serializers.ModelSerializer):
    """Shared by header groups and categories."""

    def validate_url_slug(self, value):
        cleaned = clean_url_slugs(value)
        check_url_slugs_free(cleaned, self.instance)
        return cleaned

    def validate_tagline(self, value):
        return _clean_text_map(value, 'tagline')

    def validate_description(self, value):
        return _clean_text_map(value, 'description')

    def validate_image_url(self, value):
        return to_key(value.strip())

    def create(self, validated_data):
        # Without an explicit position a new section goes last.
        model = self.Meta.model
        if 'order' not in validated_data:
            validated_data['order'] = _next(model.objects.all(), 'order')
        group = validated_data.get('group')
        if model is Category and group and 'group_order' not in validated_data:
            validated_data['group_order'] = _next(group.categories.all(), 'group_order')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # A newly picked image replaces one uploaded in the Django admin.
        if 'image_url' in validated_data and instance.image:
            instance.image = None
        # A category moved to another group goes last there.
        group = validated_data.get('group')
        if (
            isinstance(instance, Category)
            and group
            and group != instance.group
            and 'group_order' not in validated_data
        ):
            validated_data['group_order'] = _next(group.categories.all(), 'group_order')
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image_url'] = _image_out(
            instance.image, instance.image_url, self.context.get('request')
        )
        return data


class NavGroupWriteSerializer(_SectionWriteSerializer):
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
            'image_url',
        ]

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields['slug'].read_only = True  # categories and URLs point at it
        return fields

    def validate_label(self, value):
        cleaned = _clean_text_map(value, 'label')
        if not cleaned:
            raise serializers.ValidationError('A name is required.')
        return cleaned


class CategoryWriteSerializer(_SectionWriteSerializer):
    group = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=NavGroup.objects.all(),
        allow_null=True,
        required=False,
    )
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Category
        fields = [
            'id',
            'slug',
            'name',
            'name_i18n',
            'order',
            'group',
            'group_order',
            'show_in_nav',
            'featured',
            'url_slug',
            'tagline',
            'description',
            'image_url',
            'hero_image_url',
        ]
        extra_kwargs = {'slug': {'allow_unicode': True}}

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields['slug'].read_only = True  # articles and URLs point at it
        return fields

    def validate_name_i18n(self, value):
        cleaned = _clean_text_map(value, 'name_i18n')
        if not cleaned:
            raise serializers.ValidationError('A name is required.')
        return cleaned

    def validate_hero_image_url(self, value):
        return to_key(value.strip())

    def validate(self, attrs):
        names = attrs.get('name_i18n')
        if names:
            # The plain name is the fallback wherever a locale is missing.
            attrs['name'] = next(
                names[code] for code in ('en', *LOCALES) if names.get(code)
            )
        elif self.instance is None:
            raise serializers.ValidationError({'name_i18n': 'A name is required.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['hero_image_url'] = (
            to_url(instance.hero_image_url, self.context.get('request')) or ''
        )
        return data


# ---- Footer (SiteSettings) ----


class ContactSerializer(serializers.Serializer):
    email = serializers.EmailField(allow_blank=True, default='')
    phone = serializers.CharField(allow_blank=True, default='', max_length=40)
    address = serializers.JSONField(default=dict)

    def validate_address(self, value):
        return _clean_text_map(value, 'address')


class SocialLinkSerializer(serializers.Serializer):
    network = serializers.ChoiceField(choices=SOCIAL_NETWORKS)
    url = serializers.URLField(max_length=500)


class SponsorSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    name = serializers.JSONField()
    url = serializers.URLField(max_length=500, allow_blank=True, default='')
    logo = serializers.CharField(max_length=500, allow_blank=True, default='')

    def validate_name(self, value):
        cleaned = _clean_text_map(value, 'name')
        if not cleaned:
            raise serializers.ValidationError('A name is required.')
        return cleaned

    def validate_logo(self, value):
        return to_key(value.strip())


class FooterSerializer(serializers.Serializer):
    """The footer part of SiteSettings: contact, social links, sponsors."""

    contact = ContactSerializer()
    social = SocialLinkSerializer(many=True)
    sponsors = SponsorSerializer(many=True)

    def validate_social(self, value):
        networks = [item['network'] for item in value]
        if len(networks) != len(set(networks)):
            raise serializers.ValidationError('Each network can be listed once.')
        return value

    def validate_sponsors(self, value):
        # Sponsors keep their id (the site keys them by it); new ones get the next.
        next_id = max((item.get('id') or 0 for item in value), default=0) + 1
        seen = set()
        for item in value:
            if not item.get('id') or item['id'] in seen:
                item['id'] = next_id
                next_id += 1
            seen.add(item['id'])
            if not item['logo']:
                item.pop('logo')
        return value

    def save_to(self, site):
        data = self.validated_data
        site.contact = dict(data['contact'])
        site.social = [dict(item) for item in data['social']]
        site.sponsors = [dict(item) for item in data['sponsors']]
        site.save()
        return site


def footer_payload(site, request):
    contact = site.contact or {}
    return {
        'contact': {
            'email': contact.get('email', ''),
            'phone': contact.get('phone', ''),
            'address': contact.get('address') or {},
        },
        'social': site.social or [],
        'sponsors': [
            {**item, 'logo': to_url(item.get('logo'), request) or ''}
            for item in (site.sponsors or [])
        ],
    }


# ---- About page ----


def _map_images(node, fn):
    if isinstance(node, dict):
        return {
            key: (
                fn(item)
                if key in IMAGE_KEYS and isinstance(item, str)
                else _map_images(item, fn)
            )
            for key, item in node.items()
        }
    if isinstance(node, list):
        return [_map_images(item, fn) for item in node]
    return node


def about_to_keys(content):
    return _map_images(content, to_key)


def about_to_urls(content, request):
    return _map_images(content, lambda value: to_url(value, request))


class AboutSerializer(serializers.Serializer):
    content = serializers.JSONField()

    def validate_content(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Expected an object.')
        if len(str(value).encode()) > MAX_ABOUT_BYTES:
            raise serializers.ValidationError('The page is too large.')
        return about_to_keys(value)
