from rest_framework import serializers
from .models import DSOrder, DSOrderItem


class DSOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.product_name", read_only=True
    )

    class Meta:
        model = DSOrderItem
        fields = "__all__"


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
        fields = "__all__"
  
class DSOrderSerializerTrack(serializers.ModelSerializer):
    ds_name = serializers.CharField(source='ds_user.party_name', read_only=True)
    crm_name = serializers.CharField(source='assigned_crm.name', read_only=True)

    class Meta:
        model = DSOrder
        fields = [
            'id', 'order_id', 'ds_name', 'crm_name', 'created_at'
        ]

