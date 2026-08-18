from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from config.views import CustomTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('shows/', include('show.urls')),
    path('auth/', include('social_login.urls')),
    path('hita/', include('hita.urls')),
    path('eldorg/', include('eldorg.urls')),
    path('ai/', include('ai.urls')),
    path('hita_arab_festival/', include('hita_arab_festival.urls')),
    path('global_festival/', include('global_festival.urls')),
    path('alt_spaces_festival/', include('alt_spaces_festival.urls')),
    path('hita_evaluation/', include('hita_evaluation.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
