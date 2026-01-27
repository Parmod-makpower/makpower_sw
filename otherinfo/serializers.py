# serializers.py
from rest_framework import serializers
from .models import SamplingSheet, NotInStockReport, Mahotsav

class SamplingSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SamplingSheet
        fields = "__all__"


class NotInStoctSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotInStockReport
        fields = "__all__"



class MahotsavSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mahotsav
        fields = "__all__"
