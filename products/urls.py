from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, SchemeViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'schemes', SchemeViewSet, basename='scheme')

urlpatterns = [
    path('', include(router.urls)),
]
