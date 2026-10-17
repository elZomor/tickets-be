from django.db import models


class CommentLike(models.Model):
    user = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_comment_likes',
    )
    comment = models.ForeignKey(
        to='third_side.Comment', on_delete=models.CASCADE, related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'comment'], name='uniq_like_per_user_comment'
            )
        ]

    def __str__(self):
        return f'{self.user_id} likes {self.comment_id}'
