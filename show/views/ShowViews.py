import math
from rest_framework import mixins, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from config.pagination import CustomPagination
from show.models import Show
from show.models.Show import ShowStatus
from show.serializer import ShowViewSerializer


class ShowViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    serializer_class = ShowViewSerializer
    queryset = Show.objects.filter(status=ShowStatus.APPROVED.value)
    pagination_class = CustomPagination

    def get_authenticators(self):
        if self.request.method == 'GET':
            return []
        return super().get_authenticators()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().order_by('created_at')
        serializer = ShowViewSerializer(queryset, many=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        return Response('Create Show', status=status.HTTP_201_CREATED)
