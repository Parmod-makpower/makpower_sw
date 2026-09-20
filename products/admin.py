from django.contrib import admin

from .models import (
    Product,
    SaleName,
    Scheme,
    SchemeCondition,
    SchemeReward,
    ProductPriceHistory,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'product_id',
        'product_name',
        'rack_no',
        'live_stock',
        'virtual_stock',
        'mumbai_stock',
    )


admin.site.register(SaleName)
admin.site.register(Scheme)
admin.site.register(SchemeCondition)
admin.site.register(SchemeReward)


@admin.register(ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'old_price',
        'new_price',
        'old_ds_price',
        'new_ds_price',
        'changed_by',
        'changed_at',
        'applicable_from',
    )

    list_filter = (
        'applicable_from',
        'changed_by__role',
    )

    search_fields = (
        'product__product_name',
        'product__product_id',
        'changed_by__user_id',
        'changed_by__name',
    )

    ordering = ('-changed_at',)