from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('shows/', include('show.urls')),
    path('clerk/', include('clerk.urls')),
]
