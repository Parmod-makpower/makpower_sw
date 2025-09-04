
from django.urls import path
from .views import SSOrderCreateView, SSOrderHistoryView, CRMOrderListView, CRMOrderVerifyView,CRMVerifiedOrderHistoryView, CRMVerifiedOrderCompareView, get_orders_by_order_id


urlpatterns = [
    path("ss-orders/create/", SSOrderCreateView.as_view(), name="ss-order-create"),
    path('ss-orders/history/', SSOrderHistoryView.as_view(), name='ss-order-history'),
    path("crm/orders/", CRMOrderListView.as_view(), name="crm-orders-list"),
    path("crm/orders/<int:order_id>/verify/", CRMOrderVerifyView.as_view(), name="crm-order-verify"),
    path("crm/verified/", CRMVerifiedOrderHistoryView.as_view(), name="crm-verified-list"),
    path("crm/verified/<int:crm_order_id>/compare/", CRMVerifiedOrderCompareView.as_view(), name="crm-verified-compare"),
    path("dispatch-orders/<str:order_id>/", get_orders_by_order_id, name="get_orders_by_order_id"),

]
