
from django.urls import path
from .views import SSOrderCreateView, SSOrderHistoryView, CRMOrderListView, DeleteOrderListView, CRMOrderVerifyView,CRMVerifiedOrderHistoryView, get_orders_by_order_id, UpdateOrderStatusView, punch_order_to_sheet, DeleteSingleOrderView


urlpatterns = [
    path("ss-orders/create/", SSOrderCreateView.as_view(), name="ss-order-create"),
    path('ss-orders/history/', SSOrderHistoryView.as_view(), name='ss-order-history'),
    path("delete/orders/", DeleteOrderListView.as_view(), name="delete-orders-list"),
    path("delete/orders/<int:id>/", DeleteSingleOrderView.as_view(), name="delete-order"),

    path("crm/orders/", CRMOrderListView.as_view(), name="crm-orders-list"),
    path("crm/orders/<int:order_id>/verify/", CRMOrderVerifyView.as_view(), name="crm-order-verify"),
    path("crm/verified/", CRMVerifiedOrderHistoryView.as_view(), name="crm-verified-list"),
    path("crm/verified/<int:pk>/status/", UpdateOrderStatusView.as_view(), name="crm-verified-status"),
    path("dispatch-orders/<str:order_id>/", get_orders_by_order_id, name="get_orders_by_order_id"),
    path('punch-to-sheet/', punch_order_to_sheet, name='punch-to-sheet'),
]
