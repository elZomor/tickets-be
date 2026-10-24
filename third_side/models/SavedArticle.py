from django.db import models


class SavedArticle(models.Model):
    user = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_saved_articles',
    )
    article = models.ForeignKey(
        to='third_side.Article',
        on_delete=models.CASCADE,
        related_name='saved_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'article'], name='uniq_saved_article'
            )
        ]

    def __str__(self):
        return f'{self.user_id} saved {self.article_id}'
