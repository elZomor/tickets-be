from rest_framework.routers import DefaultRouter

from hita.views import (
    PerformerViewSet,
    DepartmentViewSet,
    StudyTypeViewSet,
    HITALocationViewSet,
    HitaMemberViewSet,
    SkillsViewSet,
    ContactTypeViewSet,
    ExperienceViewSet,
    AchievementViewSet,
    PublicChannelsViewSet,
    ContactDetailsViewSet, GalleryViewSet,
)

router = DefaultRouter(trailing_slash=False)

router.register(r"performers", PerformerViewSet, basename="performer")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"contact-types", ContactTypeViewSet, basename="contact_types")
router.register(r"skills", SkillsViewSet, basename="skills")
router.register(r"experiences", ExperienceViewSet, basename="experiences")
router.register(r"gallery", GalleryViewSet, basename="gallery")
router.register(r"achievements", AchievementViewSet, basename="achievements")
router.register(r"public-channels", PublicChannelsViewSet, basename="public_channels")
router.register(r"contact-details", ContactDetailsViewSet, basename="contact_details")
router.register(r"study-types", StudyTypeViewSet, basename="study_types")
router.register(r"locations", HITALocationViewSet, basename="location")
router.register(r"members", HitaMemberViewSet, basename="member")

urlpatterns = router.urls
