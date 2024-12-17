from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage

from utils.code_utils import validate_file_size, get_upload_path


class ShowReel(models.Model):
    performer = models.OneToOneField(
        'hita.Performer', on_delete=models.CASCADE, related_name='show_reel'
    )
    file = models.FileField(storage=S3Boto3Storage(), validators=[validate_file_size])
    thumbnail = models.FileField(upload_to=get_upload_path, null=True, blank=True)
