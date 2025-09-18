from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ( ProductViewSet,ProductBulkTemplateDownload,ProductBulkUpload, SaleNameViewSet, SaleNameBulkUploadView,
    SchemeViewSet,get_all_products_with_salenames, get_inactive_products, update_live_stock
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'sale-names', SaleNameViewSet)
router.register(r'schemes', SchemeViewSet)


urlpatterns = [
    path('sale-names/bulk-upload/', SaleNameBulkUploadView.as_view(), name='sale-name-bulk-upload'),
    path("products/bulk-template/", ProductBulkTemplateDownload.as_view(), name="product-bulk-template"),
    path("products/bulk-upload/", ProductBulkUpload.as_view(), name="product-bulk-upload"),
    path('products/inactive/', get_inactive_products, name="inactive-products"),  
    path('all-products/', get_all_products_with_salenames),
     path("update_live_stock/", update_live_stock),
    path('', include(router.urls)),
]

