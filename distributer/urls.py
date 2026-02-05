from django.urls import path
from .views import DSOrderCreateView, DSMyLatestOrdersView, DS_orders_by_role, DSOrderDetailsView

urlpatterns = [
    path("ds-orders/create/", DSOrderCreateView.as_view(), name="ds-order-create"),
    path("ds/orders/my-latest/", DSMyLatestOrdersView.as_view()),
    path('ds/by-role/',DS_orders_by_role, name='ds-by-role'),
    path("ds/order-details/<str:order_id>/", DSOrderDetailsView.as_view()),

]
