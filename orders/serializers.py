from rest_framework import serializers

from .models import (
    SSOrder,
    SSOrderItem,
    CRMVerifiedOrder,
    CRMVerifiedOrderItem,
    DispatchRecord,
)

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

    # =========================================================
    # SS ORDER ITEMS
    # =========================================================

    def get_ss_items(self, obj):
        items = getattr(obj, "_track_ss_items", None)

        if items is None:
            items = (
                obj.items
                .select_related("product")
                .all()
            )

        return [
            {
                "product_id": item.product.product_id,
                "product_name": item.product.product_name,
                "quantity": item.quantity,
                "price": item.price,
                "is_scheme_item": item.is_scheme_item,
            }
            for item in items
        ]

    # =========================================================
    # CRM VERIFIED DATA
    # =========================================================

    def get_crm_data(self, obj):
        crm_record = getattr(obj, "_track_crm_record", None)

        if crm_record is None:
            crm_record = (
                obj.crm_verified_versions
                .select_related("crm_user")
                .prefetch_related(
                    "items__product",
                )
                .first()
            )

        if not crm_record:
            return None

        crm_items = getattr(obj, "_track_crm_items", None)

        if crm_items is None:
            crm_items = (
                crm_record.items
                .select_related("product")
                .all()
            )

        return {
            "crm_user": (
                getattr(crm_record.crm_user, "name", None)
                or getattr(crm_record.crm_user, "username", "")
                or ""
            ),

            "status": crm_record.status,

            "verified_at": crm_record.verified_at,

            "items": [
                {
                    "product_id": item.product.product_id,
                    "product_name": item.product.product_name,
                    "quantity": item.quantity,
                    "is_rejected": item.is_rejected,
                }
                for item in crm_items
            ],
        }

    # =========================================================
    # NEW DISPATCH SYSTEM
    # =========================================================

    def get_dispatch_data(self, obj):
        """
        NEW SOURCE:

            DispatchRecord
                ↓
            CRMVerifiedOrderItem
                ↓
            CRMVerifiedOrder
                ↓
            SSOrder

        Old DispatchOrder is NOT used anywhere here.
        """

        crm_record = getattr(obj, "_track_crm_record", None)

        if crm_record is None:
            crm_record = (
                obj.crm_verified_versions
                .prefetch_related(
                    "items__product",
                    "items__dispatch_record",
                )
                .first()
            )

        if not crm_record:
            return []

        crm_items = getattr(obj, "_track_crm_items", None)

        if crm_items is None:
            crm_items = list(
                crm_record.items
                .select_related("product")
                .prefetch_related("dispatch_record")
                .all()
            )

        dispatch_data = []

        for crm_item in crm_items:

            try:
                dispatch_record = crm_item.dispatch_record
            except DispatchRecord.DoesNotExist:
                dispatch_record = None

            if not dispatch_record:
                continue

            dispatch_data.append(
                {
                    # Frontend existing structure preserved
                    "product": crm_item.product.product_name,

                    "quantity": dispatch_record.quantity,

                    "order_packed_time": (
                        dispatch_record.order_packed_time
                    ),

                    # Extra fields are safe for existing frontend
                    "crm_item_id": crm_item.id,

                    "dispatch_location": (
                        dispatch_record.dispatch_location
                    ),
                }
            )

        # Latest packed item first.
        dispatch_data.sort(
            key=lambda item: (
                item["order_packed_time"] is not None,
                item["order_packed_time"] or "",
            ),
            reverse=True,
        )

        return dispatch_data
    

class SSOrderSerializerTrack(serializers.ModelSerializer):
    ss_name = serializers.CharField(source='ss_user.party_name', read_only=True)
    crm_name = serializers.CharField(source='assigned_crm.name', read_only=True)

    class Meta:
        model = SSOrder
        fields = [
            'id', 'order_id', 'ss_name', 'crm_name',
            'total_amount', 'note','status', 'created_at'
        ]


class HROrderListSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(read_only=True)
    ss_user_name = serializers.CharField(source="ss_user.name", read_only=True)
    ss_party_name = serializers.CharField(source="ss_user.party_name", read_only=True)
    crm_name = serializers.CharField(source="assigned_crm.name", read_only=True)

    class Meta:
        model = SSOrder
        fields = [
            "id",
            "order_id",
            "ss_user_name",
            "ss_party_name",
            "crm_name",
            "status",
            "note",
            "notes",
            "created_at",
        ]


# =========================================================
# DISPATCH RECORD DASHBOARD SERIALIZER
# =========================================================

class DispatchRecordSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(
        source="crm_item.crm_order.original_order.order_id",
        read_only=True,
    )

    product = serializers.CharField(
        source="crm_item.product.product_name",
        read_only=True,
    )

    crm_item_id = serializers.IntegerField(
        source="crm_item.id",
        read_only=True,
    )

    class Meta:
        model = DispatchRecord

        fields = [
            "id",
            "crm_item_id",
            "order_id",
            "product",
            "quantity",
            "dispatch_location",
            "order_packed_time",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


