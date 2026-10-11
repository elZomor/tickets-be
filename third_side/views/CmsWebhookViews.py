import hmac

from django.conf import settings
from rest_framework import mixins
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from third_side.models import SyncedArticle
from third_side.serializers import SyncedArticleSerializer


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
            # Payload fires this webhook once per save, and concurrent saves
            # (e.g. saving one locale right after another) can have their
            # requests arrive out of order. Drop any delivery that is not
            # newer than what we already have, so a stale request can't
            # clobber a locale's content with an older webhook's payload.
            existing = SyncedArticle.objects.filter(payload_id=doc.get('id')).first()
            incoming_updated_at = doc.get('updatedAt')
            if existing and incoming_updated_at and existing.data.get('updatedAt'):
                if incoming_updated_at <= existing.data.get('updatedAt'):
                    return Response({'ok': True, 'skipped': 'stale'}, status=200)

            SyncedArticle.objects.update_or_create(
                payload_id=doc.get('id'), defaults={'data': doc}
            )

        return Response({'ok': True}, status=200)


class SyncedArticleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = SyncedArticle.objects.all()
    serializer_class = SyncedArticleSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    lookup_field = 'payload_id'
