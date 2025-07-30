# orders/admin.py

from django.contrib import admin
from .models import SSOrder, SSOrderItem, CRMVerifiedOrder, CRMVerifiedOrderItem, CRMVerifiedOrderScheme

class SSOrderItemInline(admin.TabularInline):
    model = SSOrderItem
    extra = 0

@admin.register(SSOrder)
class SSOrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'ss', 'total_quantity', 'total_price', 'placed_at']
    inlines = [SSOrderItemInline]

class CRMVerifiedOrderItemInline(admin.TabularInline):
    model = CRMVerifiedOrderItem
    extra = 0

@admin.register(CRMVerifiedOrder)
class CRMVerifiedOrderAdmin(admin.ModelAdmin):
    list_display = ['ss_order', 'verified_by', 'status', 'total_quantity', 'total_price', 'verified_at']
    inlines = [CRMVerifiedOrderItemInline]

admin.site.register(CRMVerifiedOrderScheme)