from rest_framework.routers import DefaultRouter

from hita.views import PerformerViewSet

router = DefaultRouter(trailing_slash=False)

router.register(r"performers", PerformerViewSet, basename="performer")

urlpatterns = router.urls
