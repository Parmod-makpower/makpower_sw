from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CargoDetailsViewSet

router = DefaultRouter()
router.register(r'cargo-details', CargoDetailsViewSet, basename='cargo-details')

urlpatterns = [
    path('', include(router.urls)),
]
