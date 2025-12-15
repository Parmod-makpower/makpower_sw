from django.urls import path
from .views import DSOrderCreateView, DSMyLatestOrdersView

urlpatterns = [
    path("ds-orders/create/", DSOrderCreateView.as_view(), name="ds-order-create"),
    path("ds/orders/my-latest/", DSMyLatestOrdersView.as_view()),
]
