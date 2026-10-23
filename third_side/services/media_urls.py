"""Uploaded images are stored by storage key and turned into URLs on read.

A storage URL can be signed and expire (S3), so saving it would break the image
later. Writes keep only the key (`third_side/media/x.png`); reads turn it into
the public URL (the media Worker in production, never a raw S3 link). External
or already-absolute URLs pass through.
"""

import copy
from urllib.parse import quote, urlsplit

from django.conf import settings
from django.core.files.storage import default_storage

KEY_ROOT = 'third_side/'
_ABSOLUTE = ('http://', 'https://', '//', '/')


def to_key(value):
    """The storage key behind an uploaded file's URL; anything else unchanged."""
    if not isinstance(value, str) or not value:
        return value
    if not value.startswith(_ABSOLUTE):
        return value  # already a key
    path = urlsplit(value).path
    start = path.find(f'/{KEY_ROOT}')
    return path[start + 1 :] if start != -1 else value


def file_url(name, request=None):
    """The public URL of a stored file, by its storage key."""
    host = settings.MEDIA_PUBLIC_HOST
    if host:
        return f"{host.rstrip('/')}/{quote(name)}"
    url = default_storage.url(name)
    if url.startswith('/') and request is not None:
        return request.build_absolute_uri(url)
    return url


def to_url(value, request=None):
    """A usable URL for a stored key (or the value itself when it is a URL)."""
    if not isinstance(value, str) or not value or value.startswith(_ABSOLUTE):
        return value
    return file_url(value, request)


def _walk(node, fn):
    if isinstance(node, dict):
        if node.get('type') == 'upload' and isinstance(node.get('value'), dict):
            fn(node['value'])
        for child in node.get('children') or []:
            _walk(child, fn)


def _has_upload(node):
    found = []
    _walk(node, found.append)
    return bool(found)


def content_to_keys(content):
    """Editor content ready to store: image nodes keep the key, not the URL."""
    if not isinstance(content, dict) or not _has_upload(content.get('root')):
        return content
    content = copy.deepcopy(content)
    _walk(content['root'], lambda media: media.update(url=to_key(media.get('url'))))
    return content


def content_to_urls(content, request=None):
    """Content for readers/editors: image nodes carry a fresh URL."""
    if not isinstance(content, dict) or not _has_upload(content.get('root')):
        return content
    content = copy.deepcopy(content)
    _walk(
        content['root'],
        lambda media: media.update(url=to_url(media.get('url'), request)),
    )
    return content
