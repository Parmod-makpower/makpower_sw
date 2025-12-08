from rest_framework import serializers
from .models import  Product, SaleName, Scheme, SchemeCondition, SchemeReward


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
