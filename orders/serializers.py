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


# For Compare (CRM side only)
class CRMVerifiedOrderForCompareItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = CRMVerifiedOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price']


class CRMVerifiedOrderForCompareSerializer(serializers.ModelSerializer):
    items = CRMVerifiedOrderForCompareItemSerializer(many=True, read_only=True)
    crm_name = serializers.CharField(source='crm_user.name', read_only=True)

    class Meta:
        model = CRMVerifiedOrder
        fields = ['id', 'crm_name', 'verified_at', 'status', 'notes', 'total_amount', 'items']


# ==========================
# CRM History Serializers
# ==========================

class CRMVerifiedOrderItemHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = CRMVerifiedOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price']


class CRMVerifiedOrderHistorySerializer(serializers.ModelSerializer):
    items = CRMVerifiedOrderItemHistorySerializer(many=True, read_only=True)
    original_order_id = serializers.IntegerField(source='original_order.id', read_only=True)
    order_id = serializers.CharField(source='original_order.order_id', read_only=True)
    crm_name = serializers.CharField(source='crm_user.name', read_only=True)
    party_name = serializers.CharField(source='original_order.ss_user.party_name', read_only=True)


    class Meta:
        model = CRMVerifiedOrder
        fields = [
            'id', 'order_id', 'original_order_id', 'status','crm_name','party_name',
            'notes', 'total_amount', 'verified_at', 'items'
        ]


# ==========================
# Compare Serializer
# ==========================

class CompareRowSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    product_name = serializers.CharField()
    ss_qty = serializers.IntegerField()
    crm_qty = serializers.IntegerField()
    delta = serializers.IntegerField()


class CRMVerifiedOrderDetailSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='original_order.order_id', read_only=True)
    original_order_detail = SSOrderForCompareSerializer(source='original_order', read_only=True)
    verified_order_detail = CRMVerifiedOrderForCompareSerializer(source='*', read_only=True)
    compare = serializers.SerializerMethodField()

    class Meta:
        model = CRMVerifiedOrder
        fields = [
            'id', 'order_id',
            'original_order_detail',
            'verified_order_detail',
            'compare',
        ]

    def get_compare(self, obj):
        # SS side items
        ss_items = obj.original_order.items.all()
        ss_map = {
            it.product_id: {
                "product": it.product_id,
                "product_name": getattr(it.product, "product_name", ""),
                "ss_qty": int(it.quantity)
            }
            for it in ss_items
        }

        # CRM side items
        crm_items = obj.items.all()
        crm_map = {
            it.product_id: {
                "product": it.product_id,
                "product_name": getattr(it.product, "product_name", ""),
                "crm_qty": int(it.quantity)
            }
            for it in crm_items
        }

        product_ids = sorted(set(list(ss_map.keys()) + list(crm_map.keys())))
        rows = []
        for pid in product_ids:
            name = (crm_map.get(pid) or ss_map.get(pid)).get("product_name", "")
            ss_q = ss_map.get(pid, {}).get("ss_qty", 0)
            crm_q = crm_map.get(pid, {}).get("crm_qty", 0)
            rows.append({
                "product": pid,
                "product_name": name,
                "ss_qty": ss_q,
                "crm_qty": crm_q,
                "delta": crm_q - ss_q
            })
        return CompareRowSerializer(rows, many=True).data
