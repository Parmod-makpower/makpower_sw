# serializers.py
from rest_framework import serializers
from .models import SamplingSheet

class SamplingSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SamplingSheet
        fields = "__all__"
