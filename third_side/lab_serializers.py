"""Serializers of the Lab: programs, registrations, certificates, templates.

Reads (`?lang=`) are shaped for the frontend; `LabProgramWriteSerializer` is the
admin panel's shape (all locales), also returned by GET lab-programs/{id}/doc.
"""

from rest_framework import serializers

from third_side.i18n import LOCALES, RETIRED_LOCALES, clean_locale, localize
from third_side.models import (
    Certificate,
    CertificateTemplate,
    Critic,
    LabProgram,
    LabRegistration,
)
from third_side.services import lab
from third_side.services.media_urls import (
    content_to_keys,
    content_to_urls,
    file_url,
    to_key,
    to_url,
)


def _lang(serializer):
    request = serializer.context.get('request')
    return clean_locale(request.query_params.get('lang') if request else None)


def _request(serializer):
    return serializer.context.get('request')


def program_cover(program, request=None):
    if program.cover:
        return file_url(program.cover.name, request)
    return to_url(program.cover_url, request) or None


def program_summary(program, lang, request=None):
    """The small program card used inside registrations and certificates."""
    return {
        'id': program.id,
        'kind': program.kind,
        'title': localize(program.title_i18n, lang, program.slug),
        'slug': localize(program.slug_i18n, lang, program.slug),
        'paths': lab.program_paths(program),
        'cover': program_cover(program, request),
        'starts_on': program.starts_on,
        'ends_on': program.ends_on,
    }


def _locales_of(*maps):
    have = {
        code
        for values in maps
        if isinstance(values, dict)
        for code, text in values.items()
        if text
    }
    return [code for code in LOCALES if code in have]


class LabProgramReadSerializer(serializers.ModelSerializer):
    """A program for readers. The list leaves `body` out (context `detail`)."""

    class Meta:
        model = LabProgram
        fields = [
            'id',
            'kind',
            'mode',
            'language',
            'starts_on',
            'ends_on',
            'hours',
            'is_featured',
            'certificate_enabled',
        ]

    def to_representation(self, obj):
        lang = _lang(self)
        request = _request(self)
        data = super().to_representation(obj)
        data.update(
            slug=localize(obj.slug_i18n, lang, obj.slug),
            slugs={code: localize(obj.slug_i18n, code, obj.slug) for code in LOCALES},
            paths=lab.program_paths(obj),
            title=localize(obj.title_i18n, lang, obj.slug),
            summary=localize(obj.summary_i18n, lang),
            cover=program_cover(obj, request),
            location=localize(obj.location_i18n, lang),
            locales=_locales_of(obj.title_i18n, obj.summary_i18n),
            partner={
                'name': localize(obj.partner_name_i18n, lang),
                'logo': to_url(obj.partner_logo_url, request) or None,
            },
            registration={
                'mode': obj.registration_mode,
                'state': lab.registration_state(obj),
                'capacity': obj.capacity,
                'seats_left': lab.seats_left(obj),
                'deadline': obj.registration_deadline,
                'external_url': obj.external_url or None,
            },
            sessions_count=len(obj.sessions or []),
        )
        if not self.context.get('detail'):
            return data
        body = obj.body_i18n or {}
        doc = body.get(lang) or body.get('ar') or next(iter(body.values()), None)
        data['body'] = content_to_urls(doc, request) if doc else None
        data['sessions'] = [
            {
                'date': item.get('date') or None,
                'time': item.get('time') or '',
                'title': localize(item.get('title_i18n'), lang),
            }
            for item in obj.sessions or []
        ]
        critics = {
            c.pk: c
            for c in Critic.objects.filter(
                pk__in=[
                    i.get('critic') for i in obj.instructors or [] if i.get('critic')
                ]
            )
        }
        data['instructors'] = [
            self._instructor(item, critics, lang, request)
            for item in obj.instructors or []
        ]
        return data

    @staticmethod
    def _instructor(item, critics, lang, request):
        critic = critics.get(item.get('critic'))
        photo = to_url(item.get('photo_url'), request) or None
        writer_slug = None
        if critic is not None:
            writer_slug = localize(critic.slug_i18n, lang, str(critic.pk))
            if not photo and critic.photo:
                photo = file_url(critic.photo.name, request)
            elif not photo:
                photo = to_url(critic.photo_url, request) or None
        return {
            'name': localize(item.get('name_i18n'), lang)
            or (localize(critic.name_i18n, lang, critic.name) if critic else ''),
            'bio': localize(item.get('bio_i18n'), lang),
            'photo': photo,
            'writer_slug': writer_slug,
        }


def _text_map(value, field, keep_lists=False):
    """{locale: text} (or {locale: [texts]}) with known locales only."""
    if value in (None, ''):
        return {}
    if not isinstance(value, dict):
        raise serializers.ValidationError({field: 'Expected {locale: value}.'})
    cleaned = {}
    for locale, item in value.items():
        if locale in RETIRED_LOCALES:
            continue
        if locale not in LOCALES:
            raise serializers.ValidationError({field: f'Unknown language "{locale}".'})
        if keep_lists:
            if not isinstance(item, list):
                raise serializers.ValidationError(
                    {field: 'Expected a list per language.'}
                )
            items = [str(x).strip() for x in item if str(x).strip()]
            if items:
                cleaned[locale] = items
            continue
        if not isinstance(item, str):
            raise serializers.ValidationError({field: 'Texts must be strings.'})
        if item.strip():
            cleaned[locale] = item.strip()
    return cleaned


class LabProgramWriteSerializer(serializers.ModelSerializer):
    """Admin panel writes and GET lab-programs/{id}/doc."""

    registrations_count = serializers.SerializerMethodField()
    certificates_count = serializers.SerializerMethodField()

    class Meta:
        model = LabProgram
        fields = [
            'id',
            'slug',
            'slug_i18n',
            'kind',
            'title_i18n',
            'summary_i18n',
            'body_i18n',
            'cover_url',
            'mode',
            'location_i18n',
            'language',
            'starts_on',
            'ends_on',
            'sessions',
            'hours',
            'instructors',
            'partner_name_i18n',
            'partner_logo_url',
            'registration_mode',
            'external_url',
            'capacity',
            'registration_deadline',
            'is_published',
            'is_featured',
            'certificate_enabled',
            'cert_title_i18n',
            'cert_kind_label_i18n',
            'cert_program_title_i18n',
            'cert_details_i18n',
            'cert_issued_on',
            'cert_template_ar',
            'cert_template_en',
            'registrations_count',
            'certificates_count',
        ]
        extra_kwargs = {'slug': {'required': False}}

    def get_registrations_count(self, obj) -> int:
        return obj.registrations.exclude(status='cancelled').count()

    def get_certificates_count(self, obj) -> int:
        return obj.certificates.filter(revoked=False).count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = _request(self)
        if not data['cover_url'] and instance.cover:
            data['cover_url'] = instance.cover.name
        data['cover_url'] = to_url(data['cover_url'], request)
        data['partner_logo_url'] = to_url(data['partner_logo_url'], request)
        data['body_i18n'] = {
            code: content_to_urls(doc, request)
            for code, doc in (instance.body_i18n or {}).items()
        }
        data['instructors'] = [
            {**item, 'photo_url': to_url(item.get('photo_url'), request) or ''}
            for item in instance.instructors or []
        ]
        return data

    def validate_cover_url(self, value):
        return to_key(value)

    def validate_partner_logo_url(self, value):
        return to_key(value)

    def validate_language(self, value):
        if value not in LOCALES:
            raise serializers.ValidationError('Unknown language.')
        return value

    def validate_body_i18n(self, value):
        if value in (None, ''):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('Expected {locale: document}.')
        cleaned = {}
        for code, doc in value.items():
            if code in RETIRED_LOCALES or not doc:
                continue
            if code not in LOCALES or not isinstance(doc, dict):
                raise serializers.ValidationError(f'Bad document for "{code}".')
            cleaned[code] = content_to_keys(doc)
        return cleaned

    def validate_sessions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Expected a list.')
        rows = []
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError('Each session is an object.')
            rows.append(
                {
                    'date': str(item.get('date') or ''),
                    'time': str(item.get('time') or '')[:40],
                    'title_i18n': _text_map(item.get('title_i18n'), 'sessions'),
                }
            )
        return rows

    def validate_instructors(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Expected a list.')
        rows = []
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError('Each instructor is an object.')
            critic = item.get('critic')
            rows.append(
                {
                    'name_i18n': _text_map(item.get('name_i18n'), 'instructors'),
                    'bio_i18n': _text_map(item.get('bio_i18n'), 'instructors'),
                    'photo_url': to_key(item.get('photo_url') or ''),
                    'critic': int(critic) if str(critic or '').isdigit() else None,
                }
            )
        return rows

    def validate(self, attrs):
        for field in (
            'title_i18n',
            'summary_i18n',
            'location_i18n',
            'partner_name_i18n',
            'cert_title_i18n',
            'cert_kind_label_i18n',
            'cert_program_title_i18n',
        ):
            if field in attrs:
                attrs[field] = _text_map(attrs[field], field)
        if 'cert_details_i18n' in attrs:
            attrs['cert_details_i18n'] = _text_map(
                attrs['cert_details_i18n'], 'cert_details_i18n', keep_lists=True
            )
        if 'slug_i18n' in attrs:
            attrs['slug_i18n'] = {
                code: lab_slug(text)
                for code, text in _text_map(attrs['slug_i18n'], 'slug_i18n').items()
                if lab_slug(text)
            }

        def current(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, None) if self.instance else None

        errors = {}
        title = current('title_i18n') or {}
        if not title:
            errors['title_i18n'] = 'A program needs a title.'
        starts, ends = current('starts_on'), current('ends_on')
        if starts and ends and ends < starts:
            errors['ends_on'] = 'The program cannot end before it starts.'
        if current('registration_mode') == 'external' and not current('external_url'):
            errors['external_url'] = 'An external registration needs a link.'
        if errors:
            raise serializers.ValidationError(errors)

        slugs = current('slug_i18n') or {}
        for code in LOCALES:
            if not slugs.get(code) and title.get(code):
                slugs[code] = lab_slug(title[code])
        attrs['slug_i18n'] = slugs
        if not current('slug'):
            base = slugs.get('en') or slugs.get('ar') or 'program'
            attrs['slug'] = _unique_program_slug(base, self.instance)
        return attrs


def lab_slug(text):
    from third_side.i18n import slug_from_title

    return slug_from_title(text or '')[:110]


def _unique_program_slug(base, instance):
    from third_side.i18n import unique_slug

    others = LabProgram.objects.all()
    if instance is not None:
        others = others.exclude(pk=instance.pk)
    return unique_slug(base, lambda s: others.filter(slug=s).exists())


class MyRegistrationSerializer(serializers.ModelSerializer):
    program = serializers.SerializerMethodField()

    class Meta:
        model = LabRegistration
        fields = ['id', 'status', 'attended', 'created_at', 'program']

    def get_program(self, obj) -> dict:
        return program_summary(obj.program, _lang(self), _request(self))


class RegistrationAdminSerializer(serializers.ModelSerializer):
    """A row of the admin panel's participants table."""

    user = serializers.SerializerMethodField()
    certificate = serializers.SerializerMethodField()

    class Meta:
        model = LabRegistration
        fields = [
            'id',
            'program',
            'user',
            'status',
            'answers',
            'attended',
            'note',
            'created_at',
            'certificate',
        ]
        read_only_fields = ['id', 'program', 'user', 'answers', 'created_at']

    def get_user(self, obj) -> dict:
        user = obj.user
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'gender': user.gender,
        }

    def get_certificate(self, obj) -> str | None:
        codes = self.context.get('certificate_codes')
        if codes is not None:
            return codes.get(obj.user_id)
        found = Certificate.objects.filter(
            program_id=obj.program_id, user_id=obj.user_id, language='ar'
        ).first()
        return found.code if found else None


def _english_state(certificate):
    english = next(
        (c for c in certificate.translations.all() if c.language == 'en'), None
    )
    if english is not None:
        return {'status': 'issued', 'code': english.code}
    if certificate.english_name_requested:
        return {'status': 'waiting', 'code': None}
    return {'status': 'none', 'code': None}


class MyCertificateSerializer(serializers.ModelSerializer):
    program = serializers.SerializerMethodField()
    paths = serializers.SerializerMethodField()
    english = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'code',
            'language',
            'participant_name',
            'issued_at',
            'revoked',
            'program',
            'paths',
            'english',
        ]

    def get_program(self, obj) -> dict:
        return program_summary(obj.program, _lang(self), _request(self))

    def get_paths(self, obj) -> dict:
        return lab.certificate_paths(obj.code)

    def get_english(self, obj) -> dict | None:
        if obj.language != 'ar':
            return None
        return _english_state(obj)


class CertificateVerifySerializer(serializers.ModelSerializer):
    """What anyone holding the code may see."""

    valid = serializers.SerializerMethodField()
    program = serializers.SerializerMethodField()
    paths = serializers.SerializerMethodField()
    issued_date = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'code',
            'language',
            'participant_name',
            'issued_at',
            'issued_date',
            'valid',
            'program',
            'paths',
        ]

    def get_valid(self, obj) -> bool:
        return not obj.revoked

    def get_program(self, obj) -> dict:
        return program_summary(obj.program, _lang(self), _request(self))

    def get_paths(self, obj) -> dict:
        return lab.certificate_paths(obj.code)

    def get_issued_date(self, obj) -> str:
        return (obj.context or {}).get('issued_date', '')


class CertificateAdminSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    source_code = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'id',
            'code',
            'program',
            'user',
            'language',
            'participant_name',
            'issued_at',
            'revoked',
            'source_code',
            'english_name_requested',
        ]
        read_only_fields = [
            'id',
            'code',
            'program',
            'user',
            'language',
            'issued_at',
            'source_code',
            'english_name_requested',
        ]

    def get_user(self, obj) -> dict:
        return {'id': obj.user_id, 'name': obj.user.name, 'email': obj.user.email}

    def get_source_code(self, obj) -> str | None:
        return obj.source.code if obj.source_id else None

    def update(self, instance, validated_data):
        name = validated_data.get('participant_name')
        if name:
            instance.context = {**(instance.context or {}), 'participant_name': name}
        return super().update(instance, validated_data)


class CertificateTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateTemplate
        fields = ['id', 'name', 'language', 'html', 'is_default', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    def validate_language(self, value):
        if value not in LOCALES:
            raise serializers.ValidationError('Unknown language.')
        return value

    def validate_html(self, value):
        from django.template import Template, TemplateSyntaxError

        try:
            Template(value)
        except TemplateSyntaxError as error:
            raise serializers.ValidationError(f'Template error: {error}')
        return value

    def save(self, **kwargs):
        template = super().save(**kwargs)
        if template.is_default:
            CertificateTemplate.objects.filter(
                language=template.language, is_default=True
            ).exclude(pk=template.pk).update(is_default=False)
        return template
