from rest_framework.routers import DefaultRouter

from social_login.views import GoogleLogin

router = DefaultRouter(trailing_slash=False)

router.register(r"google", GoogleLogin, basename="google-auth")

urlpatterns = router.urls
