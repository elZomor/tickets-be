from rest_framework.routers import DefaultRouter

from ai.views import AIViewSet
from eldorg.views import ScriptViewSet
from hita_arab_festival.views import (
    ArabFestivalViewSet,
    ShowViewSet,
    ArticleViewSet,
    CommentViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'festivals', ArabFestivalViewSet, basename='hita_arab_festivals-view')
router.register(r'shows', ShowViewSet, basename='hita_arab_shows-view')
router.register(r'articles', ArticleViewSet, basename='hita_arab_articles-view')
router.register(r'comments', CommentViewSet, basename='hita_arab_comments-view')
urlpatterns = router.urls
