from django.db import models


class ActivityAction(models.TextChoices):
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    DELETE = 'delete', 'Delete'
    UPLOAD = 'upload', 'Upload'
    REVIEW = 'review', 'Review'


class ActivityObject(models.TextChoices):
    ARTICLE = 'article', 'Article'
    FESTIVAL_POST = 'festival_post', 'Festival post'
    CATEGORY = 'category', 'Category'
    CRITIC = 'critic', 'Critic'
    MEDIA = 'media', 'Media'
    TAG = 'tag', 'Tag'
    REPORT = 'report', 'Report'
    NAV_GROUP = 'nav_group', 'Nav group'
    ABOUT = 'about', 'About page'
    SITE_SETTINGS = 'site_settings', 'Site settings'


class ActivityLog(models.Model):
    """One editor action in the admin, with the changed fields before and after.

    Append-only: written by `third_side.services.audit`, read by the admin's
    Activity log page. The actor is also kept as a name/email snapshot so the
    row stays readable after the account is gone.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        'third_side.ThirdSideUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activity',
    )
    actor_name = models.CharField(max_length=150, blank=True, default='')
    actor_email = models.EmailField(blank=True, default='')
    action = models.CharField(max_length=10, choices=ActivityAction.choices)
    object_type = models.CharField(max_length=20, choices=ActivityObject.choices)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=255, blank=True, default='')
    # {"<field>": {"before": ..., "after": ...}}; only the changed fields.
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['actor', 'created_at']),
        ]

    def __str__(self):
        return f'{self.action} {self.object_type} #{self.object_id}'
