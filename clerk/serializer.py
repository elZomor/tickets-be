import hashlib
import hmac

from rest_framework import serializers
from rest_framework.exceptions import APIException

from config.constants import CLERK_SIGNING_SECRET


class ClerkSerializer(serializers.Serializer):
    clerk_signature = serializers.CharField(required=True)
    body = serializers.JSONField(required=True)

    def validate(self, data):
        expected_signature = hmac.new(
            CLERK_SIGNING_SECRET.encode('utf-8'),
            msg=data.get('body').encode('utf-8'),
            digestmod=hashlib.sha256,
        ).hexdigest()
        signature = data.get('clerk_signature')
        if not hmac.compare_digest(signature, expected_signature):
            raise APIException()