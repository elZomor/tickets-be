from django.core.exceptions import ValidationError
from django.db import models

from utils.code_utils import get_upload_path


def validate_file_size(value):
    max_size_mb = 50
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size must be less than {max_size_mb} MB")


class ShowReel(models.Model):
    performer = models.OneToOneField(
        'hita.Performer', on_delete=models.CASCADE, related_name='show_reel'
    )
    file = models.FileField(upload_to=get_upload_path, validators=[validate_file_size])
