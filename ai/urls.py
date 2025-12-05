from rest_framework.routers import DefaultRouter

from ai.views import AIViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'query', AIViewSet, basename='query-view')
urlpatterns = router.urls
