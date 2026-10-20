import os
import uuid
from datetime import datetime

from django.utils.deconstruct import deconstructible
from django.utils.text import slugify


def upload_to_critic_photo(instance, filename):
    instance_id = instance.id or "unassigned"
    name = slugify(instance.name or "unknown")
    created_at = datetime.now().strftime('%Y-%m-%d')
    ext = os.path.splitext(filename)[1]
    file_name = f"{instance_id}_{name}_{created_at}{ext}"
    return os.path.join('media', 'third_side', 'critic', 'photo', file_name)


@deconstructible
class AsciiUploadTo:
    """`upload_to` that stores files under an ASCII-only key.

    Uploaded names can be Arabic or percent-encoded; such keys do not survive
    the media worker (it reads the path as the key). Keep the readable ASCII
    part of the name, add a short id so keys stay unique, and fall back to the
    id alone when nothing readable is left.
    """

    def __init__(self, folder):
        self.folder = folder

    def __call__(self, instance, filename):
        stem, ext = os.path.splitext(os.path.basename(filename))
        name = slugify(stem)[:60]  # ASCII only: Arabic letters drop out
        unique = uuid.uuid4().hex[:8]
        key = f"{name}-{unique}" if name else uuid.uuid4().hex
        return f"{self.folder}/{key}{ext.lower()}"
