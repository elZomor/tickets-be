from rest_framework import mixins, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from third_side.models import Rating
from third_side.serializers import RatingSerializer


class RatingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = RatingSerializer
    queryset = Rating.objects.order_by('-id')

    def get_authenticators(self):
        if getattr(self.request, 'method', None) == 'GET':
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if getattr(self.request, 'method', None) == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

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
