from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Festival FK field on Form -> URL prefix the festival's site calls (see config/urls.py).
FESTIVAL_FIELDS = {
    'arab_festival': 'hita_arab_festival',
    'global_festival': 'global_festival',
    'alt_spaces_festival': 'alt_spaces_festival',
}


class UniqueBy(models.TextChoices):
    NONE = 'NONE', 'بدون (يسمح بأكثر من رد)'
    USER = 'USER', 'رد واحد لكل مستخدم مسجل'
    FIELD = 'FIELD', 'رد واحد لكل قيمة حقل (مثل الموبايل)'


class Form(models.Model):
    # Exactly one festival is set: festivals live in separate apps/models.
    arab_festival = models.ForeignKey(
        'hita_arab_festival.ArabFestival',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='forms',
    )
    global_festival = models.ForeignKey(
        'global_festival.GlobalFestival',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='forms',
    )
    alt_spaces_festival = models.ForeignKey(
        'alt_spaces_festival.AltSpacesFestival',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='forms',
    )
    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True)
    title = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    description_en = models.TextField(blank=True, default='')
    notice = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Information note shown above the fields.',
    )
    notice_en = models.CharField(max_length=500, blank=True, default='')
    warning = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Important warning shown above the fields '
        '(e.g. all data must be written in Arabic).',
    )
    warning_en = models.CharField(max_length=500, blank=True, default='')
    success_message = models.TextField(
        blank=True, default='', help_text='Shown after a successful submission.'
    )
    success_message_en = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    max_responses = models.PositiveIntegerField(
        null=True, blank=True, help_text='Leave empty for no limit.'
    )
    requires_login = models.BooleanField(
        default=False, help_text='Only signed-in (Google) users can submit.'
    )
    unique_by = models.CharField(
        max_length=8, choices=UniqueBy.choices, default=UniqueBy.NONE
    )
    unique_field_key = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text='Field key used when "unique by" is a field value (e.g. mobile).',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def festival(self):
        for field in FESTIVAL_FIELDS:
            if getattr(self, f'{field}_id'):
                return getattr(self, field)
        return None

    def clean(self):
        chosen = [f for f in FESTIVAL_FIELDS if getattr(self, f'{f}_id')]
        if len(chosen) != 1:
            raise ValidationError('Choose exactly one festival for this form.')

    def closed_reason(self, response_count=None):
        """None when the form accepts responses, otherwise a reason code."""
        now = timezone.now()
        if not self.is_active:
            return 'CLOSED'
        if self.opens_at and now < self.opens_at:
            return 'NOT_OPEN_YET'
        if self.closes_at and now >= self.closes_at:
            return 'CLOSED'
        if self.max_responses is not None:
            if response_count is None:
                response_count = self.responses.count()
            if response_count >= self.max_responses:
                return 'FULL'
        return None
