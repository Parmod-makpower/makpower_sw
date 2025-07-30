
from products.models import Product  
from rest_framework import serializers
from .models import SSOrder, SSOrderItem, CRMVerifiedOrder, CRMVerifiedOrderItem, CRMVerifiedOrderScheme

class SSOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SSOrderItem
        fields = ['product_id', 'sale_name', 'price', 'quantity']



class SSOrderSerializer(serializers.ModelSerializer):
    items = SSOrderItemSerializer(many=True)

    class Meta:
        model = SSOrder
        fields = ['id', 'order_id', 'ss', 'crm','party_name', 'total_quantity', 'total_price', 'placed_at', 'applied_schemes', 'items']
        read_only_fields = ['placed_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        applied_schemes = validated_data.get('applied_schemes', [])

        # ✅ Inject sale_name in all scheme reward products
        for scheme in applied_schemes:
            for reward in scheme.get('rewards', []):
                product_id = reward.get('product_id')
                if product_id and 'sale_name' not in reward:
                    try:
                        product = Product.objects.get(product_id=product_id)
                        reward['sale_name'] = product.product_name
                    except Product.DoesNotExist:
                        reward['sale_name'] = product_id  # fallback

        # ✅ Save updated applied_schemes with sale_name included
        validated_data['applied_schemes'] = applied_schemes

        # ✅ Create order and items
        order = SSOrder.objects.create(**validated_data)
        for item_data in items_data:
            SSOrderItem.objects.create(order=order, **item_data)

        return order


class CRMVerifiedOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMVerifiedOrderItem
        fields = ['product_id', 'sale_name', 'price', 'quantity']

class CRMVerifiedOrderSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMVerifiedOrderScheme
        fields = ['product_id', 'sale_name', 'quantity', 'is_auto_applied']

class CRMVerifiedOrderSerializer(serializers.ModelSerializer):
    items = CRMVerifiedOrderItemSerializer(many=True)
    verified_schemes = CRMVerifiedOrderSchemeSerializer(many=True, required=False)
    ss_order = serializers.PrimaryKeyRelatedField(queryset=SSOrder.objects.all())  # ✅ keep only this line
    

    class Meta:
        model = CRMVerifiedOrder
        fields = [
            'id', 'ss_order', 'verified_by', 'total_quantity', 'total_price',
            'status', 'notes', 'verified_at', 'items', 'verified_schemes'
        ]
        read_only_fields = ['verified_at']


    def create(self, validated_data):
        items_data = validated_data.pop('items')
        schemes_data = validated_data.pop('verified_schemes', [])

        order = CRMVerifiedOrder.objects.create(**validated_data)
        for item_data in items_data:
            CRMVerifiedOrderItem.objects.create(order=order, **item_data)
        for scheme_data in schemes_data:
            CRMVerifiedOrderScheme.objects.create(order=order, **scheme_data)
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        schemes_data = validated_data.pop('verified_schemes', None)

        # Update main fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                CRMVerifiedOrderItem.objects.create(order=instance, **item_data)

        if schemes_data is not None:
            instance.verified_schemes.all().delete()
            for scheme_data in schemes_data:
                CRMVerifiedOrderScheme.objects.create(order=instance, **scheme_data)

        return instance
    
# serializers.py

class CRMVerifiedOrderListSerializer(serializers.ModelSerializer):
    ss_order = SSOrderSerializer(read_only=True)  # ✅ order_id & party_name show honge

    class Meta:
        model = CRMVerifiedOrder
        fields = ['id', 'ss_order', 'status', 'verified_at']

# serializers.py

class CRMVerifiedOrderDetailSerializer(serializers.ModelSerializer):
    ss_order = SSOrderSerializer()
    items = CRMVerifiedOrderItemSerializer(many=True)
    verified_schemes = CRMVerifiedOrderSchemeSerializer(many=True)
    
    class Meta:
        model = CRMVerifiedOrder
        fields = [
            "id",
            "ss_order",
            "verified_by",
            "verified_at",
            "status",
            "notes",
            "total_quantity",
            "total_price",
            "items",
            "verified_schemes"
        ]


# orders/serializers.py (bottom me add karo)

from accounts.models import CustomUser
from .models import CRMVerifiedOrder

class SimpleCRMSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'mobile']

class AdminVerifiedOrderListSerializer(serializers.ModelSerializer):
    ss_order = SSOrderSerializer(read_only=True)
    verified_by = SimpleCRMSerializer(read_only=True)

    class Meta:
        model = CRMVerifiedOrder
        fields = ['id', 'ss_order', 'verified_by', 'status', 'verified_at']
