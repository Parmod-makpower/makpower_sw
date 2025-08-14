
from django.urls import path
from .views import SSOrderCreateView, SSOrderHistoryView, CRMOrderListView, CRMOrderVerifyView, SSOrderTrackView,CRMVerifiedOrdersList, CRMVerifiedOrderUpdate, CRMVerifiedOrderDetail

urlpatterns = [
    path("ss-orders/create/", SSOrderCreateView.as_view(), name="ss-order-create"),
    path('ss-orders/history/', SSOrderHistoryView.as_view(), name='ss-order-history'),
    path("ss-orders/<int:order_id>/track/", SSOrderTrackView.as_view(), name="ss-order-track"),  # <-- new
    path("crm/orders/", CRMOrderListView.as_view(), name="crm-orders-list"),
    path("crm/orders/<int:order_id>/verify/", CRMOrderVerifyView.as_view(), name="crm-order-verify"),
    # LIST (CRM को अपने, Admin को सब)
    path("crm/verified-orders/", CRMVerifiedOrdersList.as_view(), name="crm-verified-orders"),

    # UPDATE
    path("crm/verified-orders/<int:pk>/update/", CRMVerifiedOrderUpdate.as_view(), name="crm-verified-order-update"),

    # NEW: DETAIL + COMPARE (CRM owner या Admin ही देख सकेंगे)
    path("crm/verified-orders/<int:pk>/detail/", CRMVerifiedOrderDetail.as_view(), name="crm-verified-order-detail"),

]
