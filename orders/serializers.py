# 📁 orders/serializers.py
from rest_framework import serializers
from django.db.models import OuterRef, Subquery
from .models import SSOrder, SSOrderItem, CRMVerifiedOrder, CRMVerifiedOrderItem, DispatchOrder


# ==========================
# SS Order Serializers

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
             'created_at','status','notes',
            'items','total_amount'
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

class OnlySSOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = SSOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'is_scheme_item']


class SS_to_CRM_Orders(serializers.ModelSerializer):
    items = OnlySSOrderItemSerializer(many=True, read_only=True)
    ss_user_name = serializers.CharField(source='ss_user.name', read_only=True)
    crm_name = serializers.CharField(source='assigned_crm.name', read_only=True)
    ss_party_name = serializers.CharField(source='ss_user.party_name', read_only=True)

    recent_rejected_items = serializers.SerializerMethodField()

    class Meta:
        model = SSOrder
        fields = [
            'id', 'order_id',
            'ss_party_name', 'ss_user', 'ss_user_name',
            'assigned_crm', 'crm_name',
            'total_amount', 'status', 'created_at',
            'items',
            'recent_rejected_items',
        ]

    def get_recent_rejected_items(self, obj):
        """
        हर product का latest CRMVerifiedOrderItem देखो।
        अगर latest rejected है → दिखाओ,
        अगर बाद में approve हो गया → हटा दो।
        """
        # Subquery: हर product का सबसे recent verification entry निकालना
        latest_subquery = (
            CRMVerifiedOrderItem.objects
            .filter(
                product=OuterRef("product"),
                crm_order__original_order__ss_user=obj.ss_user
            )
            .order_by("-crm_order__verified_at")
        )

        # Latest entry लो per product
        latest_items = (
            CRMVerifiedOrderItem.objects
            .filter(
                id=Subquery(latest_subquery.values("id")[:1])
            )
            .select_related("product", "crm_order")
            .filter(is_rejected=True)[:10]  # सिर्फ़ latest reject वाले
        )

        return [
            {
                "product": row.product.product_id,
                "product_name": row.product.product_name,
                "quantity": row.quantity,
                "last_rejected_at": row.crm_order.verified_at,
            }
            for row in latest_items
        ]


class CRMVerifiedOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = CRMVerifiedOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'is_rejected']


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
class CRMVerifiedOrderItemLiteSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = CRMVerifiedOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price']  # 👈 is_rejected हटाया


class CRMVerifiedOrderListSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='original_order.order_id', read_only=True)
    ss_party_name = serializers.CharField(source='original_order.ss_user.party_name', read_only=True)
    ss_user_name = serializers.CharField(source='original_order.ss_user.name', read_only=True)
    crm_name = serializers.CharField(source='crm_user.name', read_only=True)

    # ✅ Approved items जोड़ दिए
    items = serializers.SerializerMethodField()

    class Meta:
        model = CRMVerifiedOrder
        fields = [
            'id', 'order_id', 'ss_party_name', 'ss_user_name', 'crm_name',
            'verified_at', 'status','notes', 'total_amount', 'items'
        ]

    def get_items(self, obj):
        # हम सिर्फ़ approved_items_prefetched दिखाएँगे (क्योंकि queryset में prefetch किया है)
        if hasattr(obj, "approved_items_prefetched"):
            return CRMVerifiedOrderItemLiteSerializer(obj.approved_items_prefetched, many=True).data
        # fallback
        return CRMVerifiedOrderItemLiteSerializer(
            obj.items.filter(is_rejected=False).select_related("product"),
            many=True
        ).data


class DispatchOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatchOrder
        fields = "__all__"