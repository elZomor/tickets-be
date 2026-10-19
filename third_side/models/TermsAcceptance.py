from django.db import models


class TermsAcceptance(models.Model):
    """A user's acceptance of one terms version (written at signup)."""

    user = models.ForeignKey(
        'third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='terms_acceptances',
    )
    terms = models.ForeignKey(
        'third_side.TermsVersion',
        on_delete=models.PROTECT,
        related_name='acceptances',
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'terms'], name='third_side_unique_terms_acceptance'
            )
        ]

    def __str__(self):
        return f'{self.user_id} accepted {self.terms}'
