"""Edge + server cache for anonymous Third Side reads.

The FE renders every page on the server and fans out to a handful of public
endpoints (home, nav-groups, categories, ...), each per locale. Those reads hit
the database (and count as Supabase egress) on every page view, crawler hit and
cold Worker isolate.

For anonymous GETs on a short allowlist of public paths this middleware:
  1. serves a cached body from Django's cache (Redis in prod) for TTL seconds, and
  2. sets `Cache-Control: public, s-maxage=..., stale-while-revalidate=...` so
     Cloudflare / browsers can cache too.

Never cached: requests with an Authorization header or session cookie (editors
see drafts, readers see their own data), non-GET, non-200, and random or
counting endpoints (`ads/pick`, impressions, `{id}/read`).
"""

import hashlib
import re

from django.conf import settings
from django.core.cache import cache

_PREFIX = '/third_side/'

# First path segment after /third_side/ that is safe to share between anonymous users.
_PUBLIC_ROOTS = {
    'home',
    'nav-groups',
    'categories',
    'category-pages',
    'tags',
    'critics',
    'festivals',
    'festival-posts',
    'articles',
    'about',
    'terms',
    'footer',
}

# Per-request or per-user even when anonymous.
_NEVER = re.compile(r'/(like|read|similar-mine|mine)(/|$)')


# Query params the public views read and that are safe to key on. Anything else
# (free-text `search`, `staff`, `unread`, random junk) bypasses the cache, so a
# crawler cannot fill Redis with unique keys and an unknown filter can never be
# served a wrong cached body.
_KEY_PARAMS = {
    'lang', 'page', 'page_size', 'category', 'group', 'tag', 'critic',
    'featured', 'festival', 'article',
}
_MAX_BODY = 512 * 1024


def _cacheable_path(path: str) -> bool:
    if not path.startswith(_PREFIX):
        return False
    rest = path[len(_PREFIX):]
    root = rest.split('/', 1)[0]
    return root in _PUBLIC_ROOTS and not _NEVER.search(path)


class AnonymousReadCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.ttl = int(getattr(settings, 'THIRD_SIDE_READ_CACHE_TTL', 60))
        self.swr = int(getattr(settings, 'THIRD_SIDE_READ_CACHE_SWR', 300))

    def __call__(self, request):
        if (
            self.ttl <= 0
            or request.method != 'GET'
            or request.META.get('HTTP_AUTHORIZATION')
            or request.COOKIES.get(settings.SESSION_COOKIE_NAME)
            or not _cacheable_path(request.path)
            or not set(request.GET) <= _KEY_PARAMS
        ):
            return self.get_response(request)

        query = '&'.join(f'{k}={v}' for k, v in sorted(request.GET.items()))
        key = 'ts-read:' + hashlib.sha256(
            f'{request.path}?{query}'.encode()
        ).hexdigest()
        try:
            hit = cache.get(key)
        except Exception:
            hit = None  # cache backend down: fall through to the DB
        if hit is not None:
            response = self._rebuild(hit)
            response['X-Cache'] = 'HIT'
            return response

        response = self.get_response(request)
        if (
            response.status_code == 200
            and not response.streaming
            and len(response.content) <= _MAX_BODY
        ):
            response['Cache-Control'] = (
                f'public, max-age=0, s-maxage={self.ttl}, '
                f'stale-while-revalidate={self.swr}'
            )
            response['X-Cache'] = 'MISS'
            try:
                cache.set(
                    key,
                    (
                        response.content,
                        response.get('Content-Type', 'application/json'),
                    ),
                    self.ttl,
                )
            except Exception:
                pass
        return response

    def _rebuild(self, hit):
        from django.http import HttpResponse

        body, content_type = hit
        response = HttpResponse(body, content_type=content_type)
        response['Cache-Control'] = (
            f'public, max-age=0, s-maxage={self.ttl}, '
            f'stale-while-revalidate={self.swr}'
        )
        return response
