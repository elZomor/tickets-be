# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from rest_framework.viewsets import GenericViewSet
from django.contrib.auth import logout

from config.constants import FE_URL


class LoginViewSet(GenericViewSet):

    def list(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            response = redirect(FE_URL)

            # Set the is_logged_in cookie and user information in cookies
            response.set_cookie('is_logged_in', 'true', max_age=3600, httponly=False)
            response.set_cookie('user', user.first_name, max_age=3600, httponly=False)
            return response
        else:
            # If not authenticated, redirect to the frontend with login failure
            frontend_url = "FE_URL"
            return redirect(frontend_url)


class LogoutViewSet(GenericViewSet):
    def list(self, request, *args, **kwargs):
        logout(request)
        response = redirect(FE_URL)
        response.delete_cookie('is_logged_in')
        response.delete_cookie('user')
        return response
