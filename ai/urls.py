from rest_framework.routers import DefaultRouter

from ai.views import AIViewSet
from eldorg.views import ScriptViewSet
from show.views.FestivalsViews import FestivalViewSet
from show.views.ShowViews import ShowViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'query', AIViewSet, basename='query-view')
urlpatterns = router.urls
