# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import ( ProductViewSet,ProductBulkTemplateDownload,ProductBulkUpload, SaleNameViewSet, SaleNameBulkUploadView,
#     SchemeViewSet,get_all_products_with_salenames, get_inactive_products, get_virtual_stock, get_mumbai_stock, export_products_excel,ProductUsageReportView
# )

# router = DefaultRouter()
# router.register(r'products', ProductViewSet)
# router.register(r'sale-names', SaleNameViewSet)
# router.register(r'schemes', SchemeViewSet)


# urlpatterns = [
#     path('sale-names/bulk-upload/', SaleNameBulkUploadView.as_view(), name='sale-name-bulk-upload'),
#     path("products/bulk-template/", ProductBulkTemplateDownload.as_view(), name="product-bulk-template"),
#     path("products/bulk-upload/", ProductBulkUpload.as_view(), name="product-bulk-upload"),
#     path('products/inactive/', get_inactive_products, name="inactive-products"),  
#     path('all-products/', get_all_products_with_salenames),
#     path('virtual-stock/', get_virtual_stock),
#     path("mumbai-stock/", get_mumbai_stock),
#     path("products/export-excel/", export_products_excel, name="export-products-excel"),
#     path("usage/<int:product_id>/", ProductUsageReportView.as_view()),
#     path('', include(router.urls)),
# ]


from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProductViewSet,
    ProductBulkTemplateDownload,
    ProductBulkUpload,
    SaleNameViewSet,
    SaleNameBulkUploadView,
    SchemeViewSet,
    BulkPriceUpdateView,
    ProductPriceHistoryListView,
    get_all_products_with_salenames,
    get_inactive_products,
    get_virtual_stock,
    get_mumbai_stock,
    export_products_excel,
    ProductUsageReportView,
)


router = DefaultRouter()

router.register(r'products', ProductViewSet)
router.register(r'sale-names', SaleNameViewSet)
router.register(r'schemes', SchemeViewSet)


urlpatterns = [

    # ---------------------------------------------------------
    # Sale Names
    # ---------------------------------------------------------

    path(
        'sale-names/bulk-upload/',
        SaleNameBulkUploadView.as_view(),
        name='sale-name-bulk-upload'
    ),


    # ---------------------------------------------------------
    # Product Bulk Operations
    # ---------------------------------------------------------

    path(
        'products/bulk-template/',
        ProductBulkTemplateDownload.as_view(),
        name='product-bulk-template'
    ),

    path(
        'products/bulk-upload/',
        ProductBulkUpload.as_view(),
        name='product-bulk-upload'
    ),


    # ---------------------------------------------------------
    # Product Lists / Stock
    # ---------------------------------------------------------

    path(
        'products/inactive/',
        get_inactive_products,
        name='inactive-products'
    ),

    path(
        'all-products/',
        get_all_products_with_salenames
    ),

    path(
        'virtual-stock/',
        get_virtual_stock
    ),

    path(
        'mumbai-stock/',
        get_mumbai_stock
    ),


    # ---------------------------------------------------------
    # Product Export
    # ---------------------------------------------------------

    path(
        'products/export-excel/',
        export_products_excel,
        name='export-products-excel'
    ),


    # ---------------------------------------------------------
    # Product Usage Report
    # ---------------------------------------------------------

    path(
        'usage/<int:product_id>/',
        ProductUsageReportView.as_view()
    ),


    # =========================================================
    # PRICE MANAGEMENT
    # =========================================================


    # Bulk price update
    # POST /api/price-management/update/
    path(
        'price-management/update/',
        BulkPriceUpdateView.as_view(),
        name='price-management-update'
    ),

    # Price history
    # GET /api/price-history/
    # GET /api/price-history/?product_id=123
    # GET /api/price-history/?search=abc
    path(
        'price-history/',
        ProductPriceHistoryListView.as_view(),
        name='product-price-history'
    ),


    # ---------------------------------------------------------
    # Existing Router URLs
    # ---------------------------------------------------------

    path(
        '',
        include(router.urls)
    ),
]
