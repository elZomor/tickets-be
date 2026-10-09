from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from third_side.models.Article import Article


class Rating(models.Model):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='third_side_ratings'
    )
    article = models.ForeignKey(to=Article, on_delete=models.CASCADE, related_name='ratings')
    value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        unique_together = ('user', 'article')

    def __str__(self):
        return f'{self.user} rated {self.article} - {self.value}'
