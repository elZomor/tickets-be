from rest_framework.routers import DefaultRouter

from show.views.ShowViews import ShowViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', ShowViewSet, basename='show-view')
urlpatterns = router.urls
