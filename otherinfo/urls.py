from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    SamplingSheetViewSet,
    NotInStockViewSet,
    PassportLookupView,
    CouponSubmitView,
)

router = DefaultRouter()
router.register(r"sampling-sheet", SamplingSheetViewSet, basename="sampling-sheet")
router.register(r"not-in-stock-report",NotInStockViewSet,basename="not-in-stock-sheet")

urlpatterns = router.urls + [
    # 🔍 QR passport lookup
    path("passport-lookup/",PassportLookupView.as_view(),name="passport-lookup"),
    # 💾 Coupon submit
    path("submit-coupon/",CouponSubmitView.as_view(),name="submit-coupon"),
]
