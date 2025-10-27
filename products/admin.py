from django.contrib import admin
from .models import  Product, SaleName, Scheme, SchemeCondition, SchemeReward



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'product_name', 'quantity_type', 'cartoon_size', 'moq', 'live_stock', 'virtual_stock')

admin.site.register(SaleName)
admin.site.register(Scheme)
admin.site.register(SchemeCondition)
admin.site.register(SchemeReward)