from django.db import models

from third_side.utils import AsciiUploadTo


class LabProgramKind(models.TextChoices):
    WORKSHOP = 'workshop', 'Workshop'
    SEMINAR = 'seminar', 'Seminar'
    MASTERCLASS = 'masterclass', 'Masterclass'
    TALK = 'talk', 'Talk'
    EVENT = 'event', 'Event'
    OTHER = 'other', 'Other'


class LabProgramMode(models.TextChoices):
    IN_PERSON = 'in_person', 'In person'
    ONLINE = 'online', 'Online'
    HYBRID = 'hybrid', 'Hybrid'


class RegistrationMode(models.TextChoices):
    CLOSED = 'closed', 'Closed'
    DIRECT = 'direct', 'Direct registration'
    APPLICATION = 'application', 'Application, reviewed by the team'
    EXTERNAL = 'external', 'External link'


class LabProgram(models.Model):
    """A workshop, seminar, masterclass... of the Third Side Lab.

    Localized fields are {"ar": ..., "en": ...} maps; `slug` is the canonical
    (fallback) URL segment, `slug_i18n` the one per locale. `body_i18n` holds a
    Lexical document per locale. The cert_* fields fill the certificate
    template; empty English ones keep English certificates waiting.
    """

    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True)
    slug_i18n = models.JSONField(default=dict, blank=True)
    kind = models.CharField(
        max_length=12, choices=LabProgramKind.choices, default=LabProgramKind.WORKSHOP
    )
    title_i18n = models.JSONField(default=dict, blank=True)
    summary_i18n = models.JSONField(default=dict, blank=True)
    body_i18n = models.JSONField(default=dict, blank=True)
    cover = models.ImageField(
        upload_to=AsciiUploadTo('third_side/lab'), null=True, blank=True
    )
    cover_url = models.CharField(max_length=300, blank=True, default='')
    mode = models.CharField(
        max_length=10, choices=LabProgramMode.choices, default=LabProgramMode.IN_PERSON
    )
    location_i18n = models.JSONField(default=dict, blank=True)
    language = models.CharField(max_length=2, default='ar')
    starts_on = models.DateField()
    ends_on = models.DateField()
    # [{date, time, title_i18n}]
    sessions = models.JSONField(default=list, blank=True)
    hours = models.PositiveSmallIntegerField(null=True, blank=True)
    # [{name_i18n, bio_i18n, photo_url, critic}]
    instructors = models.JSONField(default=list, blank=True)
    partner_name_i18n = models.JSONField(default=dict, blank=True)
    partner_logo_url = models.CharField(max_length=300, blank=True, default='')

    registration_mode = models.CharField(
        max_length=12, choices=RegistrationMode.choices, default=RegistrationMode.CLOSED
    )
    external_url = models.URLField(max_length=500, blank=True, default='')
    capacity = models.PositiveIntegerField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    certificate_enabled = models.BooleanField(default=True)
    cert_title_i18n = models.JSONField(default=dict, blank=True)
    cert_kind_label_i18n = models.JSONField(default=dict, blank=True)
    cert_program_title_i18n = models.JSONField(default=dict, blank=True)
    # {ar: [..], en: [..]}: the line under the title, joined with ◆.
    cert_details_i18n = models.JSONField(default=dict, blank=True)
    cert_issued_on = models.DateField(null=True, blank=True)
    cert_template_ar = models.ForeignKey(
        to='third_side.CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    cert_template_en = models.ForeignKey(
        to='third_side.CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    mock_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-starts_on', '-id']

    def __str__(self):
        return self.slug
