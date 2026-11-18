import json

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from config.constants import ENVIRONMENT
from hita_arab_festival.models import Show
from hita_arab_festival.models.Application import (
    Application,
    NATIONAL_ID_EXTENSIONS,
    NATIONAL_ID_MAX_MB,
    SCRIPT_EXTENSIONS,
    SCRIPT_MAX_MB,
)
from hita_arab_festival.models.Article import Article
from hita_arab_festival.models.Comment import Comment
from hita_arab_festival.models.Festival import ArabFestival
from utils.validators import (
    is_arabic_text,
    normalize_egyptian_mobile,
    normalize_whatsapp,
    validate_arabic_text,
    validate_upload,
)


def build_media_url(file_field, request):
    """
    Mirror the behavior from the shows API so attachments return the absolute CDN URL.
    """
    if request and ENVIRONMENT == 'local':
        return request.build_absolute_uri(file_field.url)
    return f'https://media.play-cast.com/{file_field.name}?w=800&q=75&fmt=auto'


class ArabFestivalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArabFestival
        fields = "__all__"

    total_shows = serializers.SerializerMethodField()
    total_articles = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    def get_total_shows(self, obj):
        return obj.total_shows

    def get_total_articles(self, obj):
        return obj.festival_articles.count()

    def get_logo(self, obj):
        if obj.logo:
            return build_media_url(obj.logo, self.context.get('request'))
        return None


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = "__all__"

    article_attachments_list = serializers.SerializerMethodField()

    def get_article_attachments_list(self, obj):
        request = self.context.get('request')
        attachments = obj.article_attachments.all().order_by('position')
        return [
            build_media_url(attachment.file, request)
            for attachment in attachments
            if attachment.file
        ]


class ShowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Show
        fields = "__all__"

    is_open_for_reservation = serializers.SerializerMethodField()
    festival_name = serializers.SerializerMethodField()
    festival_slug = serializers.SerializerMethodField()
    is_comment_allowed = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()

    def get_is_open_for_reservation(self, obj):
        return obj.is_open_for_reservation

    def get_is_comment_allowed(self, obj):
        return obj.is_open_for_reservation

    def get_festival_name(self, obj: Show):
        return obj.festival.name if obj.festival else None

    def get_festival_slug(self, obj: Show):
        return obj.festival.start_date.year if obj.festival else None

    def get_poster(self, obj: Show):
        if obj.poster:
            return build_media_url(obj.poster, self.context.get('request'))
        return None


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"


MAX_ACTORS = 50
ARABIC_FIELDS = (
    'show_name',
    'director_name',
    'author',
    'directorial_vision',
    'show_summary',
)


class ApplicationCreateSerializer(serializers.ModelSerializer):
    actors = serializers.CharField()

    class Meta:
        model = Application
        fields = (
            'email',
            'show_name',
            'director_name',
            'department',
            'study_type',
            'study_phase',
            'author',
            'dramaturgy',
            'mobile',
            'whatsapp',
            'actors',
            'script',
            'directorial_vision',
            'show_summary',
            'national_id',
        )
        # Blank only for rows created before the field existed; new ones must pick.
        extra_kwargs = {'study_phase': {'required': True, 'allow_blank': False}}

    def get_fields(self):
        fields = super().get_fields()
        for name in ARABIC_FIELDS:
            fields[name].validators.append(validate_arabic_text)
        return fields

    def validate_email(self, value):
        return value.strip().lower()

    def validate_dramaturgy(self, value):
        value = (value or '').strip()
        if value and not is_arabic_text(value):
            raise serializers.ValidationError('ARABIC_ONLY', code='ARABIC_ONLY')
        return value

    def validate_mobile(self, value):
        mobile = normalize_egyptian_mobile(value)
        if not mobile:
            raise serializers.ValidationError('INVALID_MOBILE', code='INVALID_MOBILE')
        return mobile

    def validate_whatsapp(self, value):
        whatsapp = normalize_whatsapp(value)
        if not whatsapp:
            raise serializers.ValidationError(
                'INVALID_WHATSAPP', code='INVALID_WHATSAPP'
            )
        return whatsapp

    def validate_actors(self, value):
        try:
            actors = json.loads(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError('INVALID_ACTORS', code='INVALID_ACTORS')
        if not isinstance(actors, list):
            raise serializers.ValidationError('INVALID_ACTORS', code='INVALID_ACTORS')
        actors = [a.strip() for a in actors if isinstance(a, str) and a.strip()]
        if not actors or len(actors) > MAX_ACTORS:
            raise serializers.ValidationError('INVALID_ACTORS', code='INVALID_ACTORS')
        if not all(is_arabic_text(a) for a in actors):
            raise serializers.ValidationError('ARABIC_ONLY', code='ARABIC_ONLY')
        return actors

    def _validate_file(self, upload, extensions, max_mb):
        try:
            validate_upload(upload, extensions, max_mb)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages[0], code=e.code)
        return upload

    def validate_script(self, value):
        return self._validate_file(value, SCRIPT_EXTENSIONS, SCRIPT_MAX_MB)

    def validate_national_id(self, value):
        return self._validate_file(value, NATIONAL_ID_EXTENSIONS, NATIONAL_ID_MAX_MB)
