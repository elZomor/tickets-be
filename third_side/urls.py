from django.urls import path
from rest_framework.routers import DefaultRouter

from third_side.views import (
    ArticleViewSet,
    CategoryViewSet,
    CommentViewSet,
    CriticViewSet,
    ProfileMeView,
    RatingViewSet,
    ReportViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'categories', CategoryViewSet, basename='category-view')
router.register(r'critics', CriticViewSet, basename='critic-view')
router.register(r'articles', ArticleViewSet, basename='article-view')
router.register(r'ratings', RatingViewSet, basename='rating-view')
router.register(r'comments', CommentViewSet, basename='comment-view')
router.register(r'reports', ReportViewSet, basename='report-view')

urlpatterns = router.urls + [
    path('profile/me', ProfileMeView.as_view(), name='profile-me'),
]
