from django.db import models

from utils.code_utils import get_upload_path


class Gallery(models.Model):
    performer = models.ForeignKey(
        'hita.Performer', on_delete=models.CASCADE, related_name='galleries'
    )
    description = models.CharField(max_length=255)
    file = models.FileField(upload_to=get_upload_path)
    is_profile_picture = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
