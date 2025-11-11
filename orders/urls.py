
from django.urls import path
from .views import SSOrderCreateView, SSOrderHistoryView, CRMOrderListView, CRMOrderVerifyView,CRMVerifiedOrderHistoryView, get_orders_by_order_id, UpdateOrderStatusView, punch_order_to_sheet, CRMOrderDeleteView, AddItemToCRMVerifiedOrderView, CRMVerifiedItemUpdateView, CRMVerifiedItemDeleteView, hold_order, reject_order, CombinedOrderTrackView


urlpatterns = [
    path("ss-orders/create/", SSOrderCreateView.as_view(), name="ss-order-create"),
    path('ss-orders/history/', SSOrderHistoryView.as_view(), name='ss-order-history'),
    path('crm/orders/<int:order_id>/hold/', hold_order),
    path('crm/orders/<int:order_id>/reject/', reject_order),

    path("crm/orders/<int:order_id>/delete/", CRMOrderDeleteView.as_view(), name="crm-order-delete"),
    path("crm/orders/", CRMOrderListView.as_view(), name="crm-orders-list"),
    path("crm/orders/<int:order_id>/verify/", CRMOrderVerifyView.as_view(), name="crm-order-verify"),
    path("crm/verified/", CRMVerifiedOrderHistoryView.as_view(), name="crm-verified-list"),
    path("crm/verified/<int:pk>/status/", UpdateOrderStatusView.as_view(), name="crm-verified-status"),
    path("crm/verified/<int:pk>/add-item/", AddItemToCRMVerifiedOrderView.as_view(), name="add-item-crm-verified"),
    path("crm/verified/item/<int:pk>/update/", CRMVerifiedItemUpdateView.as_view(), name="crm-verified-item-update"),
    path("crm/verified/item/<int:pk>/delete/", CRMVerifiedItemDeleteView.as_view(), name="crm-verified-item-delete"),
    path('punch-to-sheet/', punch_order_to_sheet, name='punch-to-sheet'),
    path("dispatch-orders/<str:order_id>/", get_orders_by_order_id, name="get_orders_by_order_id"),

    path("track-order/<str:order_id>/", CombinedOrderTrackView.as_view())


]
