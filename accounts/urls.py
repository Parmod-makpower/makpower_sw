from django.urls import path, include
from .views import LoginView, CRMUserViewSet, SSUserViewSet, DSUserViewSet, UserHierarchyView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView


router = DefaultRouter()
router.register('crm-users', CRMUserViewSet, basename='crm-users')
router.register('ss-users', SSUserViewSet, basename='ss-users')
router.register('ds-users', DSUserViewSet, basename='ds-users')


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),

    path('hierarchy/', UserHierarchyView.as_view(), name='admin-dashboard'),
   
]
