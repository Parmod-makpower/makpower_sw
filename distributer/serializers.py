from rest_framework import serializers
from .models import DSOrder, DSOrderItem


class DSOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.product_name", read_only=True
    )

    class Meta:
        model = DSOrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "price",
            "ds_virtual_stock",
            "is_scheme_item",
        ]


class DSOrderSerializer(serializers.ModelSerializer):
    items = DSOrderItemSerializer(many=True, read_only=True)
    ds_user_name = serializers.CharField(
        source="ds_user.name", read_only=True
    )
    ds_party_name = serializers.CharField(
        source="ds_user.party_name", read_only=True
    )

    class Meta:
        model = DSOrder
        fields = [
            "id",
            "order_id",
            "ds_user",
            "ds_user_name",
            "ds_party_name",
            "total_amount",
            "status",
            "created_at",
            "items",
        ]
  