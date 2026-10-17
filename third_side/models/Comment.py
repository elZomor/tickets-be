from django.db import models

from third_side.models.Article import Article


class Comment(models.Model):
    user = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_comments',
    )
    article = models.ForeignKey(
        to=Article, on_delete=models.CASCADE, related_name='comments'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False)

    def __str__(self):
        return f'Comment by {self.user} on {self.article}'
