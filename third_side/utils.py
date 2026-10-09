import os
from datetime import datetime

from django.utils.text import slugify


def upload_to_critic_photo(instance, filename):
    instance_id = instance.id or "unassigned"
    name = slugify(instance.name or "unknown")
    created_at = datetime.now().strftime('%Y-%m-%d')
    ext = os.path.splitext(filename)[1]
    file_name = f"{instance_id}_{name}_{created_at}{ext}"
    return os.path.join('media', 'third_side', 'critic', 'photo', file_name)
