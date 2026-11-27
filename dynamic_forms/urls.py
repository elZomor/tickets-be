from django.urls import path

from dynamic_forms.views import FormDetailView, FormSubmitView

urlpatterns = [
    path('<str:slug>', FormDetailView.as_view(), name='dynamic-form-detail'),
    path('<str:slug>/responses', FormSubmitView.as_view(), name='dynamic-form-submit'),
]
