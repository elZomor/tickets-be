from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ai.services import semantic_search_performers
from utils.Response import get_successful_response


class AIViewSet(viewsets.GenericViewSet):

    @action(detail=False, methods=["post"])
    def ask(self, request):
        try:
            query = request.data.get("q")
            results = semantic_search_performers(query)
            return get_successful_response(data=results)
        except Exception as e:
            return get_successful_response(data={"error": str(e)})
