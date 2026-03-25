from rest_framework import serializers
from .models import Cargo

class CargoSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="party.party_name", read_only=True)
    party_id = serializers.IntegerField(source="party.id", read_only=True)

    class Meta:
        model = Cargo
        fields = "__all__"