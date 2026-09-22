# from django.urls import path, include
# from .views import LoginView, SSUserViewSet, UserHierarchyView, SSUserListView
# from rest_framework.routers import DefaultRouter
# from rest_framework_simplejwt.views import TokenRefreshView


# router = DefaultRouter()
# router.register('ss-users', SSUserViewSet, basename='ss-users')

# urlpatterns = [
#     path('login/', LoginView.as_view(), name='login'),
#     path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
#     path('', include(router.urls)),
#     path('hierarchy/', UserHierarchyView.as_view(), name='admin-dashboard'),
#     path("users/ss/", SSUserListView.as_view(), name="ss-user-list"),
   
# ]




from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView,
    SSUserViewSet,
    SSUserListView,
    CustomTokenRefreshView,
    SessionCheckView,
)


router = DefaultRouter()
router.register('ss-users', SSUserViewSet, basename='ss-users')


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),

    path(
        'refresh/',
        CustomTokenRefreshView.as_view(),
        name='token_refresh'
    ),

    path(
        'session-check/',
        SessionCheckView.as_view(),
        name='session-check'
    ),

    path('', include(router.urls)),


    path(
        'users/ss/',
        SSUserListView.as_view(),
        name='ss-user-list'
    ),
]