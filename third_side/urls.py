from django.urls import path
from rest_framework.routers import DefaultRouter

from third_side.views import (
    ArticleViewSet,
    CategoryViewSet,
    CmsWebhookView,
    ForgotPasswordView,
    CommentViewSet,
    CriticViewSet,
    ProfileMeView,
    RatingViewSet,
    ReportViewSet,
    ResetPasswordView,
    SignupView,
    SyncedArticleViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'categories', CategoryViewSet, basename='category-view')
router.register(r'critics', CriticViewSet, basename='critic-view')
router.register(r'articles', ArticleViewSet, basename='article-view')
router.register(r'ratings', RatingViewSet, basename='rating-view')
router.register(r'comments', CommentViewSet, basename='comment-view')
router.register(r'reports', ReportViewSet, basename='report-view')
router.register(r'cms-articles', SyncedArticleViewSet, basename='cms-article-view')

urlpatterns = [
    path('auth/signup', SignupView.as_view(), name='auth-signup'),
    path('auth/forgot-password', ForgotPasswordView.as_view(), name='auth-forgot'),
    path('auth/reset-password', ResetPasswordView.as_view(), name='auth-reset'),
    path('profile/me', ProfileMeView.as_view(), name='profile-me'),
    # Must come before router.urls — otherwise the router's `cms-articles/<payload_id>`
    # detail route swallows "webhook" as a payload_id and never reaches this view.
    path('cms-articles/webhook', CmsWebhookView.as_view(), name='cms-articles-webhook'),
] + router.urls
