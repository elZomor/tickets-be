from django.db import models

from utils.code_utils import validate_file_size


class ShowReel(models.Model):
    performer = models.OneToOneField(
        'hita.Performer', on_delete=models.CASCADE, related_name='show_reel'
    )
    file = models.FileField(storage='storages.backends.s3boto3.S3Boto3Storage', validators=[validate_file_size])
