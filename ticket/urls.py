from rest_framework.routers import DefaultRouter
from .views import TicketReservationView

router = DefaultRouter()
router.register(r'reservation', TicketReservationView, basename='ticket-reservation')

urlpatterns = router.urls
