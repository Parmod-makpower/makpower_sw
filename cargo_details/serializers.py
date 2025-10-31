from rest_framework import serializers
from .models import CargoDetails

class CargoDetailsSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.party_name', read_only=True)

    class Meta:
        model = CargoDetails
        fields = '__all__'

    def validate(self, attrs):
        user = attrs.get('user')
        if self.instance is None:  # create mode
            if CargoDetails.objects.filter(user=user).exists():
                raise serializers.ValidationError(
                    {"user": "इस यूज़र के लिए पहले से Cargo Details मौजूद हैं।"})
        else:  # update mode — allow same user
            if CargoDetails.objects.filter(user=user).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    {"user": "इस यूज़र के लिए पहले से Cargo Details मौजूद हैं।"})
        return attrs
