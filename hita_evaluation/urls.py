from rest_framework.routers import DefaultRouter

from hita_evaluation.views import DepartmentViewSet, CourseViewSet, SurveySessionViewSet

router = DefaultRouter(trailing_slash=False)

router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'sessions', SurveySessionViewSet, basename='session')

urlpatterns = router.urls
