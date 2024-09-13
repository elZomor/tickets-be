from rest_framework import viewsets, mixins
from rest_framework.response import Response

from clerk.serializer import ClerkSerializer


class ClerkViewSet(viewsets.ViewSet, mixins.CreateModelMixin):

    def create(self, request, *args, **kwargs):
        serializer_data = {
            'body': request.body,
            'svix_id': request.headers.get('svix_id'),
            'svix_timestamp': request.headers.get('svix_timestamp'),
            'svix_signature': request.headers.get('svix_signature'),
        }
        serializer = ClerkSerializer()
        serializer.validate(data=serializer_data)
        print("success", flush=True)
        return Response({'status': 'success'})
