from django.db import models


class FollowTarget(models.TextChoices):
    CRITIC = 'critic', 'Writer'
    CATEGORY = 'category', 'Category'
    NAVGROUP = 'navgroup', 'Sub-category group'
    FESTIVAL = 'festival', 'Festival'


class Follow(models.Model):
    user = models.ForeignKey(
        to='third_side.ThirdSideUser',
        on_delete=models.CASCADE,
        related_name='third_side_follows',
    )
    target_type = models.CharField(max_length=10, choices=FollowTarget.choices)
    target_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'target_type', 'target_id'], name='uniq_follow'
            )
        ]
        indexes = [models.Index(fields=['target_type', 'target_id'])]

    def __str__(self):
        return f'{self.user_id} follows {self.target_type}:{self.target_id}'
