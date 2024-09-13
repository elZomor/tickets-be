import hashlib
import hmac

from rest_framework import serializers
from rest_framework.exceptions import APIException

from config.constants import CLERK_SIGNING_SECRET
from svix import Webhook
from svix.webhooks import WebhookVerificationError


class ClerkSerializer(serializers.Serializer):
    svix_id = serializers.CharField(required=True)
    svix_timestamp = serializers.CharField(required=True)
    svix_signature = serializers.CharField(required=True)
    body = serializers.CharField(required=True)

    def validate(self, data):
        webhook = Webhook(CLERK_SIGNING_SECRET)
        try:
            webhook.verify(data.get('body'), {
                'svix-id': data.get('svix_id'),
                'svix-timestamp': data.get('svix_timestamp'),
                'svix-signature': data.get('svix_signature'),
            })
        except WebhookVerificationError as e:
            raise APIException()