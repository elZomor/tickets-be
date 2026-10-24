from rest_framework import mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import Rating
from third_side.permissions import has_perm
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
    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_scope = 'third_side_write'

    def get_queryset(self):
        queryset = Rating.objects.order_by('-id')
        if not has_perm(self.request.user, 'view_rating'):
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
