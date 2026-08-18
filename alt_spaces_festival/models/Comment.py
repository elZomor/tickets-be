from django.contrib.auth.models import User
from django.db import models

from alt_spaces_festival.models import Show


class CommentStatus(models.TextChoices):
    APPROVED = 'APPROVED', 'Approved'
    PENDING = 'PENDING', 'Pending'
    REJECTED = 'REJECTED', 'Rejected'
    INAPPROPRIATE = 'INAPPROPRIATE', 'Inappropriate'


class Comment(models.Model):
    content = models.TextField()
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='comments')
    status = models.CharField(
        choices=CommentStatus.choices, max_length=20, default=CommentStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='alt_spaces_festival_approved_comments',
        null=True,
        blank=True,
    )
