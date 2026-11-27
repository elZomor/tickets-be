from django.urls import path

from dynamic_forms.views import FormDetailView, FormListView, FormSubmitView

urlpatterns = [
    path('forms', FormListView.as_view(), name='dynamic-form-list'),
    path('forms/<str:slug>', FormDetailView.as_view(), name='dynamic-form-detail'),
    path(
        'forms/<str:slug>/responses',
        FormSubmitView.as_view(),
        name='dynamic-form-submit',
    ),
]
