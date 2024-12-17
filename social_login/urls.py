from rest_framework.routers import DefaultRouter

from social_login.views import GoogleLogin, FacebookLogin, PolicyViewSet

router = DefaultRouter(trailing_slash=False)

router.register(r"google", GoogleLogin, basename="google-auth")
router.register(r"facebook", FacebookLogin, basename="facebook-auth")
router.register(r"policy", PolicyViewSet, basename="policy")

urlpatterns = router.urls
