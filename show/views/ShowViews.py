import math
from rest_framework import mixins, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from show.models import Show
from show.models.Show import ShowStatus
from show.serializer import ShowViewSerializer


class CustomPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_size = 5

    def get_paginated_response(self, data):
        request_page_size = self.request.query_params.get('page_size')
        page_size = int(request_page_size) if request_page_size else self.page_size
        total_pages = math.ceil(self.page.paginator.count / page_size)
        return Response(
            {
                'count': self.page.paginator.count,
                'total_pages': total_pages,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data,
            }
        )


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
