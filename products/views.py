# api/views.py
from rest_framework.viewsets import ModelViewSet
from .models import Product, Scheme
from .serializer import ProductSerializer, SchemeSerializer
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination

class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100

class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        queryset = Product.objects.all().order_by("product_id")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(sale_name__icontains=search) |
                Q(category__icontains=search)
            )
        return queryset


class SchemeViewSet(ModelViewSet):
    queryset = Scheme.objects.all()
    serializer_class = SchemeSerializer