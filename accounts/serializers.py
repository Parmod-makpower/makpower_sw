from rest_framework import serializers
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'user_id','name', 'mobile', 'role', 'crm', 'ss', 'is_active', 'created_at']


class SSUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    crm_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'role', 'user_id', 'mobile', 'password', 'name', 'crm', 'crm_name',
            'party_name', 'is_active', 'created_at', 'created_by'
        ]
        read_only_fields = ['user_id', 'created_at']

    def get_crm_name(self, obj):
        if obj.crm:
            return obj.crm.name or obj.crm.mobile
        return None

    def validate_mobile(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile number must be exactly 10 digits.")
        if CustomUser.objects.filter(mobile=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This mobile number is already in use.")
        return value

    def create(self, validated_data):
        request_user = self.context['request'].user
        password = validated_data.pop('password')

        # ----- ROLE -----
        role = validated_data.get('role') or 'SS'
        validated_data['role'] = role

        # ----- created_by -----
        validated_data['created_by'] = request_user

        # ----- CRM LOGIC -----
        # Case 1: frontend sends crm=""  → store current user
        # Case 2: frontend sends no crm field → store current user
        # Case 3: frontend sends crm ID → store that ID

        crm_id = validated_data.get('crm', None)

        if not crm_id:  
            # Means empty string, None, or field missing
            validated_data['crm'] = request_user
        else:
            # Ensure crm is a real user object
            try:
                validated_data['crm'] = CustomUser.objects.get(id=crm_id.id if isinstance(crm_id, CustomUser) else crm_id)
            except:
                validated_data['crm'] = request_user

        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password and password.strip():
            instance.set_password(password)

        instance.save()
        return instance




# dealer form k liya
class SSUserSerializerDealer(serializers.ModelSerializer):
    crm_name = serializers.CharField(source="crm.name", read_only=True)
    crm_user_id = serializers.CharField(source="crm.user_id", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "user_id",
            "name",
            "party_name",
            "mobile",
            "role",
            "crm_user_id",
            "crm_name",
        ]

# dealer form k liya