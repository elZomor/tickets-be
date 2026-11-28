from django.db import models

from third_side.utils import new_certificate_code


class Certificate(models.Model):
    """An issued certificate. `context` freezes every template variable at
    issue time, so later edits of the program never change a certificate."""

    code = models.CharField(max_length=16, unique=True, default=new_certificate_code)
    user = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='lab_certificates',
    )
    program = models.ForeignKey(
        to='third_side.LabProgram',
        on_delete=models.PROTECT,
        related_name='certificates',
    )
    registration = models.ForeignKey(
        to='third_side.LabRegistration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificates',
    )
    language = models.CharField(max_length=2, default='ar')
    # The Arabic certificate an English one was made from.
    source = models.ForeignKey(
        to='self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='translations',
    )
    participant_name = models.CharField(max_length=200)
    template = models.ForeignKey(
        to='third_side.CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    context = models.JSONField(default=dict, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)
    # An English version asked for before the program had English text.
    english_name_requested = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        ordering = ['-issued_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'program', 'language'], name='uniq_certificate'
            )
        ]

    def __str__(self):
        return f'{self.code} ({self.language})'
