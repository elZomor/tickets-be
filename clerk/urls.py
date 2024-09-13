from rest_framework.routers import DefaultRouter

from clerk.views import ClerkViewSet

router = DefaultRouter()

router.register(r"user", ClerkViewSet, basename="user")

urlpatterns = router.urls
