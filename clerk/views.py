from rest_framework import viewsets
from rest_framework.response import Response

from utils.clerk_utils import clerk_secret


class ClerkViewSet(viewsets.GenericViewSet):

    @clerk_secret
    def post(self, request, *args, **kwargs):
        # request_data = request.body
        print("*" * 20, flush=True)
        print(request.body, flush=True)
        print(request.data, flush=True)
        print("*" * 20, flush=True)
        # if event_type == 'user.created':
        # elif event_type == 'user.updated':
        return Response({'status': 'success'})
