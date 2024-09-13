from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('tickets/', include('ticket.urls')),
    path('auth/', include('auth.urls')),
]
