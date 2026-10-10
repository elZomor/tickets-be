import hmac

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.models import SyncedArticle


class CmsWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        received_secret = request.headers.get('X-Webhook-Secret')
        if not hmac.compare_digest(
            received_secret or '', settings.PAYLOAD_CMS_WEBHOOK_SECRET
        ):
            return Response(status=403)

        operation = request.data.get('operation')
        doc = request.data.get('doc') or {}

        if operation == 'delete':
            SyncedArticle.objects.filter(payload_id=doc.get('id')).delete()
        else:
            SyncedArticle.objects.update_or_create(
                payload_id=doc.get('id'), defaults={'data': doc}
            )

        return Response({'ok': True}, status=200)
