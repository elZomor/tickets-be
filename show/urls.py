from rest_framework.routers import DefaultRouter

from show.views.FestivalsViews import FestivalViewSet
from show.views.ShowViews import ShowViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'festivals', FestivalViewSet, basename='festival-view')
router.register(r'', ShowViewSet, basename='show-view')
urlpatterns = router.urls
