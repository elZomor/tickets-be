from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.auth import ThirdSideJWTAuthentication
from third_side.serializers import ProfileSerializer


class ProfileMeView(APIView):
    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)
