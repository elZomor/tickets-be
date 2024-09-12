from rest_framework.routers import DefaultRouter

from .views import TicketReservationView, TheaterView, PerformanceView

router = DefaultRouter(trailing_slash=False)
router.register(r'reservation', TicketReservationView, basename='ticket-reservation')
router.register(r'theater', TheaterView, basename='theater-view')
router.register(r'performance', PerformanceView, basename='performance-view')
urlpatterns = router.urls
