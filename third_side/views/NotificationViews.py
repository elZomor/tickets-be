from django.utils import timezone
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import (
    Notification,
    NotificationPreference,
    PushSubscription,
)


class NotificationSerializer(serializers.ModelSerializer):
    read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'params',
            'count',
            'read',
            'created_at',
            'updated_at',
        ]

    def get_read(self, obj) -> bool:
        return obj.read_at is not None


class NotificationViewSet(
    mixins.ListModelMixin, mixins.DestroyModelMixin, GenericViewSet
):
    """The signed-in user's inbox, most recently active first.

    GET notifications (?unread=1), GET notifications/unread-count,
    POST notifications/{id}/read, POST notifications/read-all,
    DELETE notifications/{id}.
    """

    serializer_class = NotificationSerializer
    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_write'

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get('unread') in ('1', 'true'):
            queryset = queryset.filter(read_at__isnull=True)
        return queryset

    @action(detail=False, methods=['GET'], url_path='unread-count')
    def unread_count(self, request):
        count = Notification.objects.filter(
            recipient=request.user, read_at__isnull=True
        ).count()
        return Response({'count': count})

    @action(detail=False, methods=['POST'], url_path='read-all')
    def read_all(self, request):
        Notification.objects.filter(
            recipient=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['POST'])
    def read(self, request, pk=None):
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=['read_at'])
        return Response(NotificationSerializer(notification).data)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['push_enabled', 'status', 'profile', 'reports', 'activity', 'follows']


class NotificationPreferenceView(APIView):
    """GET/PUT notification-preferences: what the user wants pushed."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer
    throttle_scope = 'third_side_write'

    def get(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(preference).data)

    def put(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(
            preference, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    patch = put


class PushKeysSerializer(serializers.Serializer):
    p256dh = serializers.CharField(max_length=200)
    auth = serializers.CharField(max_length=100)


class PushSubscriptionSerializer(serializers.Serializer):
    """The browser's PushSubscription.toJSON(): endpoint + keys."""

    endpoint = serializers.URLField(max_length=2000)
    keys = PushKeysSerializer()

    def validate_endpoint(self, value):
        if not value.startswith('https://'):
            raise serializers.ValidationError('Push endpoints are https.')
        return value


class PushEndpointSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)


class PushSubscriptionView(APIView):
    """POST push/subscriptions registers this device for the signed-in user (a
    device that was another account's moves over); DELETE removes it."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PushSubscriptionSerializer
    throttle_scope = 'third_side_write'

    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        PushSubscription.objects.update_or_create(
            endpoint=data['endpoint'],
            defaults={
                'user': request.user,
                'p256dh': data['keys']['p256dh'],
                'auth': data['keys']['auth'],
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:300],
                'failure_count': 0,
            },
        )
        return Response(status=status.HTTP_201_CREATED)

    def delete(self, request):
        serializer = PushEndpointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PushSubscription.objects.filter(
            user=request.user, endpoint=serializer.validated_data['endpoint']
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
