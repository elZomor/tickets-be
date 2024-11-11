from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
import math


class CustomPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_size = 5

    def get_paginated_response(self, data):
        request_page_size = self.request.query_params.get('page_size')
        page_size = int(request_page_size) if request_page_size else self.page_size
        total_pages = math.ceil(self.page.paginator.count / page_size)
        request_page_number = self.request.query_params.get('page', 1)
        current_page = int(request_page_number)
        return Response(
            {
                'count': self.page.paginator.count,
                'total_pages': total_pages,
                'current_page': current_page,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data,
            }
        )
