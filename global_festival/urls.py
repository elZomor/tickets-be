from rest_framework.routers import DefaultRouter

from global_festival.views import (
    GlobalFestivalViewSet,
    ShowViewSet,
    ArticleViewSet,
    CommentViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'festivals', GlobalFestivalViewSet, basename='global_festivals-view')
router.register(r'shows', ShowViewSet, basename='global_shows-view')
router.register(r'articles', ArticleViewSet, basename='global_articles-view')
router.register(r'comments', CommentViewSet, basename='global_comments-view')
urlpatterns = router.urls
