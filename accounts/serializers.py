from rest_framework import serializers
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'user_id','name', 'mobile', 'role', 'crm', 'ss', 'is_active', 'created_at']



class CRMUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        # Removed 'email' and 'dob'
        fields = ['id', 'user_id', 'mobile', 'password', 'name', 'is_active', 'created_at']
        read_only_fields = ['user_id', 'created_at']

    def validate_mobile(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile number must be exactly 10 digits.")
        if CustomUser.objects.filter(mobile=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This mobile number is already in use.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['role'] = 'CRM'
        validated_data['created_by'] = self.context['request'].user
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

# accounts/serializers.py
from rest_framework import serializers
from .models import CustomUser

class SSUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    crm_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'user_id', 'mobile', 'password', 'name' , 'crm', 'crm_name', 'email',
            'party_name', 'dob', 'is_active', 'created_at'
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

    def validate_email(self, value):
        if value and CustomUser.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['role'] = 'SS'
        validated_data['created_by'] = self.context['request'].user
        validated_data['crm'] = self.context['request'].user
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


# ASM serializer — largely same but role -> 'ASM'
class ASMUserSerializer(SSUserSerializer):
    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['role'] = 'ASM'
        validated_data['created_by'] = self.context['request'].user
        validated_data['crm'] = self.context['request'].user
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user


class SSUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    crm_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'user_id', 'mobile', 'password', 'name' , 'crm', 'crm_name', 'email',
            'party_name', 'dob', 'is_active', 'created_at'
        ]
        read_only_fields = ['user_id', 'created_at']

    def get_crm_name(self, obj):
        if obj.crm:
            return obj.crm.name or obj.crm.mobile  # अगर name न हो तो mobile दिखा दे
        return None

    def validate_mobile(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile number must be exactly 10 digits.")
        if CustomUser.objects.filter(mobile=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This mobile number is already in use.")
        return value

    def validate_email(self, value):
        if value and CustomUser.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['role'] = 'SS'
        validated_data['created_by'] = self.context['request'].user
        validated_data['crm'] = self.context['request'].user
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        # Only update given fields (partial update friendly)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Only set password if it's provided and not blank
        if password and password.strip():
            instance.set_password(password)

        instance.save()
        return instance


class DSUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'user_id', 'mobile', 'password', 'name', 'email',
            'party_name', 'dob', 'is_active', 'created_at'
        ]
        read_only_fields = ['user_id', 'created_at']

    def validate_mobile(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile number must be exactly 10 digits.")
        if CustomUser.objects.filter(mobile=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This mobile number is already in use.")
        return value

    def validate_email(self, value):
        if value and CustomUser.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['role'] = 'DS'
        validated_data['created_by'] = self.context['request'].user
        validated_data['ss'] = self.context['request'].user
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
