# 📁 orders/serializers.py
from rest_framework import serializers
from .models import SSOrder, SSOrderItem, CRMVerifiedOrder, CRMVerifiedOrderItem, DispatchOrder


# ==========================
# SS Order Serializers

class SSOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = SSOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'ss_virtual_stock', 'is_scheme_item']


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
             'created_at','status','note',
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
        fields = ['id', 'product', 'product_name', 'quantity','ss_virtual_stock', 'price', 'is_scheme_item']


class SS_to_CRM_Orders(serializers.ModelSerializer):
    items = OnlySSOrderItemSerializer(many=True, read_only=True)

    ss_user_name = serializers.CharField(source="ss_user.name", read_only=True)
    ss_party_name = serializers.CharField(source="ss_user.party_name", read_only=True)

    crm_name = serializers.CharField(source="assigned_crm.name", read_only=True)

    class Meta:
        model = SSOrder
        fields = [
            "id",
            "order_id",
            "ss_party_name",
            "ss_user",
            "ss_user_name",
            "assigned_crm",
            "crm_name",
            "total_amount",
            "status",
            "created_at",
            "items",
            "note",
        ]


class CRMVerifiedOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = CRMVerifiedOrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'is_rejected']


class CRMVerifiedOrderSerializer(serializers.ModelSerializer):
    items = CRMVerifiedOrderItemSerializer(many=True, read_only=True)
    crm_name = serializers.CharField(source='crm_user.name', read_only=True)
    order_id = serializers.CharField(source='original_order.order_id', read_only=True)

    class Meta:
        model = CRMVerifiedOrder
        fields = [
            'id', 'order_id', 'original_order', 'crm_user', 'crm_name',
            'verified_at', 'status',  'items'
        ]

# ⚡️ Lightweight list serializer for history page (fast)
class CRMVerifiedOrderItemLiteSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = CRMVerifiedOrderItem
        fields = ['id', 'product', 'product_name', 'quantity','ss_virtual_stock']  # 👈 is_rejected हटाया



# After Verify Serializers ------------------
class VerifiedOrderHistorysSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='original_order.order_id', read_only=True)
    ss_party_name = serializers.CharField(source='original_order.ss_user.party_name', read_only=True)
    crm_name = serializers.CharField(source='crm_user.name', read_only=True)
    punched = serializers.BooleanField(read_only=True)
    ss_order_created_at = serializers.DateTimeField(source='original_order.created_at', read_only=True)

    class Meta:
        model = CRMVerifiedOrder
        fields = ['id', 'order_id', 'ss_party_name', 'punched', 'crm_name', 'ss_order_created_at', 'verified_at',]

class VerifiedOrderDetailsSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='original_order.order_id', read_only=True)
    ss_party_name = serializers.CharField(source='original_order.ss_user.party_name', read_only=True)
    ss_user_name = serializers.CharField(source='original_order.ss_user.name', read_only=True)
    crm_name = serializers.CharField(source='crm_user.name', read_only=True)
    punched = serializers.BooleanField(read_only=True)
    ss_order_created_at = serializers.DateTimeField(source='original_order.created_at', read_only=True)

    # ✅ Approved items जोड़ दिए
    items = serializers.SerializerMethodField()

    class Meta:
        model = CRMVerifiedOrder
        fields = [
            'id', 'order_id', 'ss_party_name', 'ss_user_name', 'crm_name','ss_order_created_at',
            'verified_at', 'status', 'items','punched','dispatch_location'
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



class CombinedOrderTrackSerializer(serializers.ModelSerializer):
    ss_items = serializers.SerializerMethodField()
    crm_data = serializers.SerializerMethodField()
    dispatch_data = serializers.SerializerMethodField()

    class Meta:
        model = SSOrder
        fields = [
            "order_id",
            "ss_user",
            "assigned_crm",
            "total_amount",
            "status",
            "created_at",
            "note",
            "ss_items",
            "crm_data",
            "dispatch_data",
        ]

    def get_ss_items(self, obj):
        return [
            {
                "product_id": item.product.product_id,
                "product_name": item.product.product_name,
                "quantity": item.quantity,
                "price": item.price,
                "is_scheme_item": item.is_scheme_item,
            }
            for item in obj.items.all()
        ]

    def get_crm_data(self, obj):
        crm_record = obj.crm_verified_versions.first()
        if not crm_record:
            return None
        
        return {
            "crm_user": crm_record.crm_user.name,
            "status": crm_record.status,
            "verified_at": crm_record.verified_at,
            "items": [
                {
                    "product_id": i.product.product_id,
                    "product_name": i.product.product_name,
                    "quantity": i.quantity,
                    "is_rejected": i.is_rejected,
                }
                for i in crm_record.items.all()
            ]
        }

    def get_dispatch_data(self, obj):
        dispatch_items = DispatchOrder.objects.filter(order_id=obj.order_id)
        if not dispatch_items.exists():
            return []

        return [
            {
                "product": d.product,
                "quantity": d.quantity,
                "order_packed_time": d.order_packed_time,
            }
            for d in dispatch_items
        ]


class SSOrderSerializerTrack(serializers.ModelSerializer):
    ss_name = serializers.CharField(source='ss_user.party_name', read_only=True)
    crm_name = serializers.CharField(source='assigned_crm.name', read_only=True)

    class Meta:
        model = SSOrder
        fields = [
            'id', 'order_id', 'ss_name', 'crm_name',
            'total_amount', 'note','status', 'created_at'
        ]


class DispatchOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatchOrder
        fields = "__all__"

