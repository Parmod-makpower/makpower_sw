from rest_framework import serializers
from orders.models import SSOrder, CRMVerifiedOrder, DispatchOrder
from products.models import Product

class OrderItemSmallSerializer(serializers.ModelSerializer):
    product_id = serializers.CharField(source='product.product_id')
    product_name = serializers.CharField(source='product.product_name')

    class Meta:
        model = SSOrder.items.field.related_model  # fallback - we will not rely on this, define fields manually if needed
        fields = []

# We'll build the per-order serializer similar to your CombinedOrderTrackSerializer but used inside a list

class SingleOrderForPartySerializer(serializers.ModelSerializer):
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
                "price": str(item.price),
                "is_scheme_item": item.is_scheme_item,
            }
            for item in obj.items.all()
        ]

    def get_crm_data(self, obj):
        crm_record = obj.crm_verified_versions.order_by("-verified_at").first()
        if not crm_record:
            return None

        return {
            "crm_user": getattr(crm_record.crm_user, "name", str(crm_record.crm_user)),
            "status": crm_record.status,
            "notes": crm_record.notes,
            "total_amount": str(crm_record.total_amount),
            "verified_at": crm_record.verified_at,
            "items": [
                {
                    "product_id": i.product.product_id,
                    "product_name": i.product.product_name,
                    "quantity": i.quantity,
                    "price": str(i.price),
                    "is_rejected": i.is_rejected,
                }
                for i in crm_record.items.all()
            ],
            "punched": crm_record.punched,
            "dispatch_location": crm_record.dispatch_location,
        }

    def get_dispatch_data(self, obj):
        dispatch_items = DispatchOrder.objects.filter(order_id=obj.order_id)
        if not dispatch_items.exists():
            return []

        return [
            {
                "product": d.product,
                "quantity": d.quantity,
                "row_key": d.row_key,
            }
            for d in dispatch_items
        ]


class PartyOrdersSerializer(serializers.Serializer):
    party_id = serializers.IntegerField()
    party_name = serializers.CharField()
    orders = SingleOrderForPartySerializer(many=True)
