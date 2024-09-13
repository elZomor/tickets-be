import hashlib
import hmac

from rest_framework.exceptions import APIException

from config.constants import CLERK_SIGNING_SECRET


def clerk_secret(func):
    def inner(request, *args, **kwargs):
        signature = request.headers.get('Clerk-Signature')
        if not signature:
            raise APIException()
        payload = request.data
        expected_signature = hmac.new(
            CLERK_SIGNING_SECRET.encode('utf-8'),
            msg=payload.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise APIException()
        func(*args, **kwargs)

    return inner
