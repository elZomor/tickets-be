from django.urls import path
from rest_framework.routers import DefaultRouter

from alt_spaces_festival.views import (
    AltSpacesFestivalViewSet,
    ShowViewSet,
    ArticleViewSet,
    CommentViewSet,
    UserReservationsView,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'festivals', AltSpacesFestivalViewSet, basename='alt_spaces_festivals-view')
router.register(r'shows', ShowViewSet, basename='alt_spaces_shows-view')
router.register(r'articles', ArticleViewSet, basename='alt_spaces_articles-view')
router.register(r'comments', CommentViewSet, basename='alt_spaces_comments-view')
urlpatterns = router.urls + [
    path('reservations/my', UserReservationsView.as_view(), name='alt_spaces_user-reservations'),
]
