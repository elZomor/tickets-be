from rest_framework.routers import DefaultRouter

from auth.views import LoginViewSet, LogoutViewSet

router = DefaultRouter()
router.register(r'login', LoginViewSet, basename='login_viewset')
router.register(r'logout', LogoutViewSet, basename='logout_viewset')

urlpatterns = router.urls
