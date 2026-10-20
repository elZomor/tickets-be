from django.db import models

from third_side.utils import AsciiUploadTo


class Media(models.Model):
    """An image uploaded from the admin editor, embedded in article bodies."""

    file = models.ImageField(
        upload_to=AsciiUploadTo('third_side/media'),
        width_field='width',
        height_field='height',
    )
    alt = models.CharField(max_length=255, blank=True, default='')
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, default='')
    filesize = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        'third_side.ThirdSideUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='third_side_media',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.file.name
