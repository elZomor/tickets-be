from rest_framework.routers import DefaultRouter

from eldorg.views import ScriptViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'scripts', ScriptViewSet, basename='script-view')
urlpatterns = router.urls
