from django.contrib import admin
from .models import Product, Scheme

@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ['scheme_name', 'scheme_type', 'is_active']

@admin.register(Product)
class UserAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'product_name', 'sale_name','category', 'price','live_stock', 'cartoon_size']
