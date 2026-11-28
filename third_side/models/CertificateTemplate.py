from django.db import models


class CertificateTemplate(models.Model):
    """The HTML of a certificate, in Django template syntax.

    Rendered by services/certificates.py with the variables listed there. The
    default per language is used when a program names none.
    """

    name = models.CharField(max_length=120)
    language = models.CharField(max_length=2, default='ar')
    html = models.TextField()
    is_default = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['language', 'name']

    def __str__(self):
        return f'{self.name} ({self.language})'
