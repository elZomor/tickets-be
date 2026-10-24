from django.urls import path
from rest_framework.routers import DefaultRouter

from third_side.views import (
    AboutDocView,
    AboutView,
    ActivityLogViewSet,
    AdClickView,
    AdImpressionView,
    AdPickView,
    AdViewSet,
    ArticleViewSet,
    CategoryViewSet,
    CategoryPageView,
    EditorListView,
    EmailPreviewView,
    EmailView,
    FestivalPostViewSet,
    FestivalViewSet,
    FollowsView,
    FollowView,
    FooterView,
    ForgotPasswordView,
    LoginView,
    RefreshView,
    HomeView,
    MediaUploadView,
    CommentViewSet,
    NavGroupViewSet,
    NotificationPreferenceView,
    NotificationViewSet,
    PushSubscriptionView,
    SavedArticleIdsView,
    SavedArticlesView,
    SavedArticleView,
    TagViewSet,
    CriticViewSet,
    ProfileAvatarView,
    ProfileMeView,
    RatingViewSet,
    ReportViewSet,
    ResendVerificationView,
    ResetPasswordView,
    VerifyEmailView,
    SignatureView,
    SignupView,
    SubmissionsView,
    TermsDetailView,
    TermsVersionsView,
    TermsView,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'categories', CategoryViewSet, basename='category-view')
router.register(r'nav-groups', NavGroupViewSet, basename='nav-group-view')
router.register(r'tags', TagViewSet, basename='tag-view')
router.register(r'critics', CriticViewSet, basename='critic-view')
router.register(r'festivals', FestivalViewSet, basename='festival-view')
router.register(r'festival-posts', FestivalPostViewSet, basename='festival-post-view')
router.register(r'articles', ArticleViewSet, basename='article-view')
router.register(r'ratings', RatingViewSet, basename='rating-view')
router.register(r'comments', CommentViewSet, basename='comment-view')
router.register(r'reports', ReportViewSet, basename='report-view')
router.register(r'activity-log', ActivityLogViewSet, basename='activity-log-view')
router.register(r'ads', AdViewSet, basename='ad-view')
router.register(r'notifications', NotificationViewSet, basename='notification-view')

urlpatterns = [
    path('auth/login', LoginView.as_view(), name='auth-login'),
    path('auth/refresh', RefreshView.as_view(), name='auth-refresh'),
    path('auth/signup', SignupView.as_view(), name='auth-signup'),
    path('auth/forgot-password', ForgotPasswordView.as_view(), name='auth-forgot'),
    path('auth/reset-password', ResetPasswordView.as_view(), name='auth-reset'),
    path('auth/verify-email', VerifyEmailView.as_view(), name='auth-verify-email'),
    path(
        'auth/resend-verification',
        ResendVerificationView.as_view(),
        name='auth-resend-verification',
    ),
    path('home', HomeView.as_view(), name='home'),
    path('editors', EditorListView.as_view(), name='editors'),
    path('emails', EmailView.as_view(), name='emails'),
    path('emails/preview', EmailPreviewView.as_view(), name='emails-preview'),
    path('media', MediaUploadView.as_view(), name='media-upload'),
    path('submissions', SubmissionsView.as_view(), name='submissions'),
    path('submissions/mine', SubmissionsView.as_view(), name='submissions-mine'),
    path('about', AboutView.as_view(), name='about'),
    path('about/doc', AboutDocView.as_view(), name='about-doc'),
    path('footer', FooterView.as_view(), name='footer'),
    path('terms', TermsView.as_view(), name='terms'),
    path('terms/versions', TermsVersionsView.as_view(), name='terms-versions'),
    path('terms/<str:version>', TermsDetailView.as_view(), name='terms-detail'),
    path('ads/pick', AdPickView.as_view(), name='ad-pick'),
    path('ads/<int:pk>/impression', AdImpressionView.as_view(), name='ad-impression'),
    path('ads/<int:pk>/click', AdClickView.as_view(), name='ad-click'),
    path('category-pages/<str:slug>', CategoryPageView.as_view(), name='category-page'),
    path('profile/me', ProfileMeView.as_view(), name='profile-me'),
    path('profile/me/avatar', ProfileAvatarView.as_view(), name='profile-avatar'),
    path('profile/me/signature', SignatureView.as_view(), name='profile-signature'),
    path(
        'notification-preferences',
        NotificationPreferenceView.as_view(),
        name='notification-preferences',
    ),
    path(
        'push/subscriptions', PushSubscriptionView.as_view(), name='push-subscriptions'
    ),
    path('saved-articles', SavedArticlesView.as_view(), name='saved-articles'),
    path('saved-articles/ids', SavedArticleIdsView.as_view(), name='saved-article-ids'),
    path(
        'saved-articles/<int:article_id>',
        SavedArticleView.as_view(),
        name='saved-article',
    ),
    path('follows', FollowsView.as_view(), name='follows'),
    path(
        'follows/<str:target_type>/<str:target_ref>',
        FollowView.as_view(),
        name='follow',
    ),
] + router.urls
