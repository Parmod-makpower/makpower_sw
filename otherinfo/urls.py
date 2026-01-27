# urls.py
from rest_framework.routers import DefaultRouter
from .views import SamplingSheetViewSet, NotInStockViewSet, MahotsavViewSet

router = DefaultRouter()
router.register(r'sampling-sheet', SamplingSheetViewSet, basename="sampling-sheet")
router.register(r'not-in-stock-report', NotInStockViewSet, basename="not-in-stock-sheet")
router.register(r'mahotsav-data', MahotsavViewSet, basename="mahotsav-data")

urlpatterns = router.urls
