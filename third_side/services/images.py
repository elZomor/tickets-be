"""Checks for an uploaded image before it is stored."""

from PIL import Image


def image_error(upload, max_bytes):
    """Why `upload` cannot be stored as an image, or None when it can."""
    if upload is None:
        return 'No file was sent.'
    if not (upload.content_type or '').startswith('image/'):
        return 'Only images can be uploaded.'
    if upload.size > max_bytes:
        return f'The image is larger than {max_bytes // (1024 * 1024)} MB.'
    try:
        Image.open(upload).verify()  # Pillow must be able to read it.
        upload.seek(0)
    except Exception:
        return 'This is not a valid image.'
    return None
