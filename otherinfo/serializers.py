# serializers.py
from rest_framework import serializers
from .models import SamplingSheet, NotInStockReport, PassportCouponRecord

class SamplingSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SamplingSheet
        fields = "__all__"


class NotInStoctSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotInStockReport
        fields = "__all__"



class PassportLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PassportCouponRecord
        fields = ["user_name", "passport_number"]


class CouponSubmitSerializer(serializers.Serializer):
    passport_number = serializers.CharField()
    coupon_number = serializers.CharField()
