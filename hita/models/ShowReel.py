from django.db import models

from utils.code_utils import get_upload_path, validate_file_size


class ShowReel(models.Model):
    performer = models.OneToOneField(
        'hita.Performer', on_delete=models.CASCADE, related_name='show_reel'
    )
    file = models.FileField(upload_to=get_upload_path, validators=[validate_file_size])
