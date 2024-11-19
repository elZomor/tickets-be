from rest_framework.routers import DefaultRouter

from hita.views import PerformerViewSet, DepartmentViewSet, StudyTypeViewSet, HITALocationViewSet, HitaMemberViewSet

router = DefaultRouter(trailing_slash=False)

router.register(r"performers", PerformerViewSet, basename="performer")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"study-types", StudyTypeViewSet, basename="study_types")
router.register(r"locations", HITALocationViewSet, basename="location")
router.register(r"members", HitaMemberViewSet, basename="member")

urlpatterns = router.urls
