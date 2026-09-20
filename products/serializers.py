from rest_framework import serializers
# from .models import  Product, SaleName, Scheme, SchemeCondition, SchemeReward

from .models import (
    Product,
    SaleName,
    Scheme,
    SchemeCondition,
    SchemeReward,
    ProductPriceHistory,
)

class ProductSerializer(serializers.ModelSerializer):
    sale_names = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = "__all__"

    def get_sale_names(self, obj):
        return [s.sale_name for s in obj.sale_names.all()]
    
class ProductWithSaleNameSerializer(serializers.ModelSerializer):
    sale_names = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()   # ⭐ override price field

    class Meta:
        model = Product
        fields = [
            'product_id',
            'product_name',
            'sub_category',
            'cartoon_size',
            'guarantee',
            'product_type',
            'mah',
            'price',        # ⭐ this will now come from get_price()
            'ds_price',
            'moq',
            'rack_no',
            'quantity_type',
            'live_stock',
            'mumbai_stock',
            'sale_names',
            'image',
            'image2',
            'is_active',
        ]

    def get_price(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # ⭐ If login user is DS, return ds_price instead of normal price
        if user and hasattr(user, "role") and user.role == "DS":
            return obj.ds_price

        # ⭐ For SS or public user: normal price
        return obj.price

    def get_sale_names(self, obj):
        return [s.sale_name for s in obj.sale_names.all()]


class SaleNameSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    product_id = serializers.CharField(source='product.product_id', read_only=True)

    class Meta:
        model = SaleName
        fields = "__all__"


class PriceUpdateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    new_price = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )
    new_ds_price = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    def validate(self, attrs):
        if 'new_price' not in attrs and 'new_ds_price' not in attrs:
            raise serializers.ValidationError(
                "At least one of new_price or new_ds_price is required."
            )

        return attrs


class BulkPriceUpdateSerializer(serializers.Serializer):
    applicable_from = serializers.DateField(required=True)
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255
    )
    items = PriceUpdateItemSerializer(
        many=True,
        required=True
    )

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one product is required."
            )

        product_ids = [item['product_id'] for item in value]

        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "Duplicate product_id found in items."
            )

        return value


class ProductPriceHistorySerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(
        source='product.product_id',
        read_only=True
    )
    product_name = serializers.CharField(
        source='product.product_name',
        read_only=True
    )
    changed_by_user_id = serializers.CharField(
        source='changed_by.user_id',
        read_only=True
    )
    changed_by_name = serializers.CharField(
        source='changed_by.name',
        read_only=True
    )
    changed_by_role = serializers.CharField(
        source='changed_by.role',
        read_only=True
    )

    class Meta:
        model = ProductPriceHistory
        fields = [
            'id',
            'product_id',
            'product_name',
            'old_price',
            'new_price',
            'old_ds_price',
            'new_ds_price',
            'changed_by_user_id',
            'changed_by_name',
            'changed_by_role',
            'changed_at',
            'applicable_from',
            'reason',
        ]

class SchemeConditionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = SchemeCondition
        fields = ['id', 'product', 'product_name', 'min_quantity']

class SchemeRewardSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = SchemeReward
        fields = ['id', 'product', 'product_name', 'quantity']

class SchemeSerializer(serializers.ModelSerializer):
    conditions = SchemeConditionSerializer(many=True)
    rewards = SchemeRewardSerializer(many=True)

    class Meta:
        model = Scheme
        fields = ['id', 'created_by', 'in_box', 'conditions', 'rewards']

    def create(self, validated_data):
        conditions_data = validated_data.pop('conditions', [])
        rewards_data = validated_data.pop('rewards', [])

        scheme = Scheme.objects.create(**validated_data)

        for condition in conditions_data:
            SchemeCondition.objects.create(scheme=scheme, **condition)

        for reward in rewards_data:
            SchemeReward.objects.create(scheme=scheme, **reward)

        return scheme

    def update(self, instance, validated_data):
        instance.created_by = validated_data.get('created_by', instance.created_by)
        instance.in_box = validated_data.get('in_box', instance.in_box)
        instance.save()

        instance.conditions.all().delete()
        instance.rewards.all().delete()

        for condition in validated_data.get('conditions', []):
            SchemeCondition.objects.create(scheme=instance, **condition)

        for reward in validated_data.get('rewards', []):
            SchemeReward.objects.create(scheme=instance, **reward)

        return instance
