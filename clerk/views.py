from rest_framework import viewsets, mixins
from rest_framework.response import Response


class ClerkViewSet(viewsets.ViewSet, mixins.CreateModelMixin):

    def create(self, request, *args, **kwargs):
        print("*" * 20, flush=True)
        print(request.body, flush=True)
        print(request.data, flush=True)
        print(request.headers, flush=True)
        print("*" * 20, flush=True)
        return Response({'status': 'success'})
