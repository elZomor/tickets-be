from rest_framework.routers import DefaultRouter

from hita_evaluation.views import (
    DepartmentViewSet,
    RegulationViewSet,
    CourseViewSet,
    SurveySessionViewSet,
    DashboardViewSet,
)

router = DefaultRouter(trailing_slash=False)

router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'regulations', RegulationViewSet, basename='regulation')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'sessions', SurveySessionViewSet, basename='session')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = router.urls
