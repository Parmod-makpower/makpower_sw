# 📁 orders/serializers.py
from rest_framework import serializers
from .models import SSOrder, SSOrderItem, CRMVerifiedOrder, CRMVerifiedOrderItem


# ==========================
# SS Order Serializers
# ==========================

class SSOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = SSOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'is_scheme_item']


class SSOrderSerializer(serializers.ModelSerializer):
    items = SSOrderItemSerializer(many=True, read_only=True)
    ss_user_name = serializers.CharField(source='ss_user.name', read_only=True)
    crm_name = serializers.CharField(source='assigned_crm.name', read_only=True)
    ss_party_name = serializers.CharField(source='ss_user.party_name', read_only=True)
    crm_history = serializers.SerializerMethodField()

    class Meta:
        model = SSOrder
        fields = [
            'id', 'order_id',
            'ss_party_name', 'ss_user', 'ss_user_name',
            'assigned_crm', 'crm_name',
            'total_amount', 'status', 'created_at',
            'items', 'crm_history'
        ]

    def get_crm_history(self, obj):
        return CRMVerifiedOrderSerializer(obj.crm_verified_versions.all(), many=True).data
    
class SSOrderHistorySerializer(serializers.ModelSerializer):
    items = SSOrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = SSOrder
        fields = [
            'id', 'order_id',
             'created_at','status',
            'items','total_amount'
        ]

# orders/serializers.py

class SS_to_CRM_Orders(serializers.ModelSerializer):
    items = SSOrderItemSerializer(many=True, read_only=True)
    ss_user_name = serializers.CharField(source='ss_user.name', read_only=True)
    crm_name = serializers.CharField(source='assigned_crm.name', read_only=True)
    ss_party_name = serializers.CharField(source='ss_user.party_name', read_only=True)

    class Meta:
        model = SSOrder
        fields = [
            'id', 'order_id',
            'ss_party_name', 'ss_user', 'ss_user_name',
            'assigned_crm', 'crm_name',
            'total_amount', 'status', 'created_at',
            'items'
        ]


# For Compare (SS side only)
class SSOrderForCompareItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = SSOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'is_scheme_item']


class SSOrderForCompareSerializer(serializers.ModelSerializer):
    items = SSOrderForCompareItemSerializer(many=True, read_only=True)
    ss_user_name = serializers.CharField(source='ss_user.name', read_only=True)

    class Meta:
        model = SSOrder
        fields = ['id', 'ss_user_name', 'total_amount', 'created_at', 'items']


# ==========================
# CRM Verified Order Serializers
# ==========================

class CRMVerifiedOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = CRMVerifiedOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price']


class CRMVerifiedOrderSerializer(serializers.ModelSerializer):
    items = CRMVerifiedOrderItemSerializer(many=True, read_only=True)
    crm_name = serializers.CharField(source='crm_user.name', read_only=True)
    order_id = serializers.CharField(source='original_order.order_id', read_only=True)

    class Meta:
        model = CRMVerifiedOrder
        fields = [
            'id', 'order_id', 'original_order', 'crm_user', 'crm_name',
            'verified_at', 'status', 'notes', 'total_amount', 'items'
        ]




# ⚡️ Lightweight list serializer for history page (fast)
class CRMVerifiedOrderListSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='original_order.order_id', read_only=True)
    ss_party_name = serializers.CharField(source='original_order.ss_user.party_name', read_only=True)
    ss_user_name = serializers.CharField(source='original_order.ss_user.name', read_only=True)
    crm_name = serializers.CharField(source='crm_user.name', read_only=True)


    class Meta:
        model = CRMVerifiedOrder
        fields = ['id', 'order_id', 'ss_party_name', 'ss_user_name', 'crm_name', 'verified_at', 'status', 'total_amount']




# 📊 Compare response serializer (non-model)
class CompareItemSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    product_name = serializers.CharField()
    ss_qty = serializers.IntegerField()
    crm_qty = serializers.IntegerField()
    qty_diff = serializers.IntegerField()
    ss_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    crm_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_diff = serializers.DecimalField(max_digits=10, decimal_places=2)
    ss_is_scheme_item = serializers.BooleanField()




class CRMCompareResponseSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    ss = SSOrderForCompareSerializer()
    crm = CRMVerifiedOrderSerializer()
    compare_items = CompareItemSerializer(many=True)
    totals = serializers.DictField(child=serializers.DecimalField(max_digits=12, decimal_places=2))