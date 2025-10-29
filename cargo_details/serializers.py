from rest_framework import serializers
from .models import CargoDetails

class CargoDetailsSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.party_name', read_only=True)

    class Meta:
        model = CargoDetails
        fields = '__all__'
