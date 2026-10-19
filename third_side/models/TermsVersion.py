from django.db import models
from django.utils import timezone


class TermsVersion(models.Model):
    """One published revision of the Terms & Conditions.

    A published version is never edited: a change is a new version, so what a
    user accepted stays reproducible. `content` is
      {title: {ar,en,ro},
       sections: [{heading: {..}, paragraphs: [{..}], bullets: [{..}]}]}
    with every text a {"ar": ..., "en": ..., "ro": ...} map (resolved per
    ?lang= on read).
    """

    version = models.CharField(max_length=20, unique=True)
    effective_date = models.DateField()
    is_published = models.BooleanField(default=False)
    content = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_date', '-id']

    def __str__(self):
        return f'Terms v{self.version}'

    @classmethod
    def published(cls):
        return cls.objects.filter(is_published=True)

    @classmethod
    def current(cls):
        """The latest published version already in force, or None."""
        today = timezone.localdate()
        return cls.published().filter(effective_date__lte=today).first()
