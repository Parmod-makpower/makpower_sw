
from django.urls import path
from .views import SSOrderCreateView, CRMOrderListView, CRMOrderVerifyView,FinalOrderHistoryView, UpdateOrderStatusView, punch_order_to_sheet, CRMOrderBulkDeleteView, AddItemToCRMVerifiedOrderView, CRMVerifiedItemUpdateView, CRMVerifiedItemDeleteView, hold_order, reject_order, CombinedOrderTrackView, list_orders_by_role, SimpleSSOrderCreateView, FinalOrderDetailsView, download_orders_report, hr_orders, hr_update_order_notes, DispatchExcelUploadView, OrderRecordsListView,  OrderRecordDetailView, DispatchRecordDeleteAllView, DispatchRecordListView, DispatchRecordBulkDeleteView


urlpatterns = [
    path("ss-orders/create/", SSOrderCreateView.as_view(), name="ss-order-create"),
    path('crm/orders/<int:order_id>/hold/', hold_order),
    path('crm/orders/<int:order_id>/reject/', reject_order),
    path("crm/orders/bulk-delete/", CRMOrderBulkDeleteView.as_view(), name="crm-order-bulk-delete"),
    path("crm/orders/", CRMOrderListView.as_view(), name="crm-orders-list"),
    path("crm/orders/<int:order_id>/verify/", CRMOrderVerifyView.as_view(), name="crm-order-verify"),
    # history------------
    path("crm/orders-history/", FinalOrderHistoryView.as_view(), name="crm-verified-list"),
    path("final/order-details/<str:order_id>/", FinalOrderDetailsView.as_view()),

    path("crm/verified/<int:pk>/status/", UpdateOrderStatusView.as_view(), name="crm-verified-status"),
    path("crm/verified/<int:pk>/add-item/", AddItemToCRMVerifiedOrderView.as_view(), name="add-item-crm-verified"),
    path("crm/verified/item/<int:pk>/update/", CRMVerifiedItemUpdateView.as_view(), name="crm-verified-item-update"),
    path("crm/verified/item/<int:pk>/delete/", CRMVerifiedItemDeleteView.as_view(), name="crm-verified-item-delete"),
    path('punch-to-sheet/', punch_order_to_sheet, name='punch-to-sheet'),
    path("track-order/<str:order_id>/", CombinedOrderTrackView.as_view()),
    path('orders-by-role/',list_orders_by_role, name='orders-by-role'),

    path("download-orders-report/",download_orders_report,  name="download-orders-report"),
    path("ss-orders/simple-create/", SimpleSSOrderCreateView.as_view()),

    path("hr/orders/",hr_orders, name="hr_orders",),
    path("hr/orders/<int:pk>/notes/",hr_update_order_notes, name="hr_update_order_notes",),

    # Dispatch URLS========================================================
    # Existing working upload - DO NOT CHANGE
    path("dispatch/upload-excel/", DispatchExcelUploadView.as_view(), name="dispatch-upload-excel",),
    path("dispatch/upload-excel/", DispatchExcelUploadView.as_view(),name="dispatch-upload-excel",),
    # Dashboard
    path( "dispatch/records/", DispatchRecordListView.as_view(),name="dispatch-records-list",),
    # Delete selected
    path( "dispatch/records/delete-selected/", DispatchRecordBulkDeleteView.as_view(),name="dispatch-records-delete-selected",),
    # Delete all
    path("dispatch/records/delete-all/", DispatchRecordDeleteAllView.as_view(),name="dispatch-records-delete-all",),


    # ============================================================================
    # NEW ORDER RECORDS SYSTEM
    # ============================================================================

    path("order-records/", OrderRecordsListView.as_view(),name="order-records-list",),
    path("order-records/<int:pk>/", OrderRecordDetailView.as_view(), name="order-records-detail",),

]
