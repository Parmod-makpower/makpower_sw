# orders/urls.py

from django.urls import path
from .views import SSOrderCreateView
from .views import (
    SSOrderCreateView,
    CRMVerifiedOrderCreateView,
    CRMVerifiedOrderUpdateView,
    UnverifiedSSOrdersList,CRMVerifiedOrderHistoryView,CRMVerifiedOrderDetailView,AdminVerifiedOrderHistoryView
)

urlpatterns = [
    path('ss-orders/', SSOrderCreateView.as_view(), name='ss-order-create'),
    path('crm-orders/create/', CRMVerifiedOrderCreateView.as_view(), name='crm-order-create'),
    path('crm-orders/<int:pk>/update/', CRMVerifiedOrderUpdateView.as_view(), name='crm-order-update'),
    path('crm-orders/pending/', UnverifiedSSOrdersList.as_view(), name='crm-order-pending'),
    path('crm-orders/history/', CRMVerifiedOrderHistoryView.as_view(), name='crm-order-history'),
   # urls.py
    path('crm-orders/<int:pk>/detail/', CRMVerifiedOrderDetailView.as_view(), name='crm-order-detail'),
    path('admin-orders/history/', AdminVerifiedOrderHistoryView.as_view(), name='admin-order-history'),


]
