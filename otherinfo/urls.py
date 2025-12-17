# urls.py
from rest_framework.routers import DefaultRouter
from .views import SamplingSheetViewSet

router = DefaultRouter()
router.register(r'sampling-sheet', SamplingSheetViewSet, basename="sampling-sheet")

urlpatterns = router.urls
