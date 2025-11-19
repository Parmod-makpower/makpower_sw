from django.contrib import admin
from .models import  Product, SaleName, Scheme, SchemeCondition, SchemeReward



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'product_name', 'rack_no', 'live_stock', 'virtual_stock', 'mumbai_stock')

admin.site.register(SaleName)
admin.site.register(Scheme)
admin.site.register(SchemeCondition)
admin.site.register(SchemeReward)