from rest_framework.routers import DefaultRouter

from hita.views import (
    PerformerViewSet,
    DepartmentViewSet,
    StudyTypeViewSet,
    HITALocationViewSet,
    HitaMemberViewSet,
)
from social_login.authentication import GoogleJWTAuthentication
from social_login.views import GoogleLogin

router = DefaultRouter(trailing_slash=False)

router.register(r"google", GoogleLogin, basename="google-auth")

urlpatterns = router.urls
