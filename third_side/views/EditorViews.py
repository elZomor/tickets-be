from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from third_side.auth import ThirdSideJWTAuthentication
from third_side.models import ThirdSideUser
from third_side.permissions import RequirePerm


class EditorListView(APIView):
    """GET /editors: the users an article can be assigned to. Staff who write
    articles only."""

    authentication_classes = [ThirdSideJWTAuthentication]
    permission_classes = [IsAuthenticated, RequirePerm]
    required_perms = {'get': 'add_article'}

    def get(self, request):
        editors = ThirdSideUser.objects.with_perm('review_article')
        return Response(
            [{'id': user.pk, 'name': user.display_name} for user in editors]
        )
