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

    class Meta:
        model = Product
        fields = [
            'product_id',
            'product_name',
            'sub_category',
            'cartoon_size',
            'price',
            'live_stock',
            'sale_names',  # ✅ केवल sale_names शामिल है
            'image',  # ✅ केवल sale_names शामिल है
        ]

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
        fields = ['id', 'created_by', 'conditions', 'rewards']  # Removed: name, start_date, end_date

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
        instance.save()

        instance.conditions.all().delete()
        instance.rewards.all().delete()

        for condition in validated_data.get('conditions', []):
            SchemeCondition.objects.create(scheme=instance, **condition)

        for reward in validated_data.get('rewards', []):
            SchemeReward.objects.create(scheme=instance, **reward)

        return instance
