from rest_framework import mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.models import Rating, Role
from third_side.serializers import RatingSerializer


class RatingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """A reader's own ratings. Article averages come with the article payload.

    GET /ratings?article=<id> is the signed-in user's rating(s); editors see all.
    """

    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_write'

    def get_queryset(self):
        queryset = Rating.objects.order_by('-id')
        profile = getattr(self.request.user, 'third_side_profile', None)
        if not (profile and profile.role == Role.EDITOR):
            queryset = queryset.filter(user=self.request.user)
        if self.request.query_params.get('article'):
            queryset = queryset.filter(article_id=self.request.query_params['article'])
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article = serializer.validated_data['article']
        value = serializer.validated_data['value']

        rating, created = Rating.objects.update_or_create(
            user=request.user, article=article, defaults={'value': value}
        )

        response_serializer = self.get_serializer(rating)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id:
            self.permission_denied(self.request)
        instance.delete()
