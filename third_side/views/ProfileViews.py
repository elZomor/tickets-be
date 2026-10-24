from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.auth import ThirdSideJWTAuthentication
from third_side.permissions import EmailVerified
from third_side.serializers import ProfileSerializer, ProfileUpdateSerializer
from third_side import tasks
from third_side.services.images import image_error
from third_side.services.notify import enqueue

AVATAR_MAX_BYTES = 5 * 1024 * 1024


class ProfileMeView(APIView):
    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    throttle_scope = 'third_side_write'

    def get(self, request):
        return Response(
            ProfileSerializer(request.user, context={'request': request}).data
        )

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        # The bio is public-facing text: it waits for a confirmed email.
        bio = serializer.validated_data.get('bio')
        if (
            bio is not None
            and bio != request.user.bio
            and not request.user.can_contribute
        ):
            return Response(EmailVerified.message, status=status.HTTP_403_FORBIDDEN)
        changed = [
            name
            for name, value in serializer.validated_data.items()
            if getattr(request.user, name) != value
        ]
        serializer.save()
        _notify_profile(request.user, changed)
        return Response(
            ProfileSerializer(request.user, context={'request': request}).data
        )


def _notify_profile(user, fields):
    """Tell the user their details changed (field names only, no values)."""
    if fields:
        enqueue(tasks.notify_profile_updated, user.pk, list(fields))


def _drop_file(field):
    """Delete a replaced file once the new one is committed."""
    name, storage = field.name, field.storage
    if name:
        transaction.on_commit(lambda: storage.delete(name))


class ProfileAvatarView(APIView):
    """POST (multipart: file) sets the signed-in user's photo; DELETE removes it.

    Both return the profile, as GET /profile/me does.
    """

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, EmailVerified]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ProfileSerializer
    throttle_scope = 'third_side_write'

    def _profile(self, request):
        return Response(
            ProfileSerializer(request.user, context={'request': request}).data
        )

    def post(self, request):
        upload = request.FILES.get('file')
        error = image_error(upload, AVATAR_MAX_BYTES)
        if error:
            return Response({'file': [error]}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        with transaction.atomic():
            if user.avatar:
                _drop_file(user.avatar)
            user.avatar = upload
            user.save(update_fields=['avatar'])
            _notify_profile(user, ['avatar'])
        return self._profile(request)

    def delete(self, request):
        user = request.user
        if user.avatar:
            with transaction.atomic():
                _drop_file(user.avatar)
                user.avatar = None
                user.save(update_fields=['avatar'])
                _notify_profile(user, ['avatar'])
        return self._profile(request)
