# from rest_framework import serializers
# from .models import CustomUser


# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = "__all__"


# class SSUserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, required=False, allow_blank=True)
#     crm_name = serializers.SerializerMethodField()

#     class Meta:
#         model = CustomUser
#         fields = [
#             'id', 'role', 'user_id', 'stock_location', 'mobile', 'password', 'name', 'crm', 'crm_name', 'ss',
#             'party_name', 'is_active', 'created_at', 'created_by'
#         ]
#         read_only_fields = ['user_id', 'created_at']

#     def get_crm_name(self, obj):
#         if obj.crm:
#             return obj.crm.name or obj.crm.mobile
#         return None

#     def validate_mobile(self, value):
#         if not value.isdigit() or len(value) != 10:
#             raise serializers.ValidationError("Mobile number must be exactly 10 digits.")
#         if CustomUser.objects.filter(mobile=value).exclude(id=self.instance.id if self.instance else None).exists():
#             raise serializers.ValidationError("This mobile number is already in use.")
#         return value

#     def create(self, validated_data):
#         request_user = self.context['request'].user
#         password = validated_data.pop('password')

#         # ----- ROLE -----
#         role = validated_data.get('role') or 'SS'
#         validated_data['role'] = role

#         # ----- created_by -----
#         validated_data['created_by'] = request_user

#         # ----- CRM LOGIC -----
#         # Case 1: frontend sends crm=""  → store current user
#         # Case 2: frontend sends no crm field → store current user
#         # Case 3: frontend sends crm ID → store that ID

#         crm_id = validated_data.get('crm', None)

#         if not crm_id:  
#             # Means empty string, None, or field missing
#             validated_data['crm'] = request_user
#         else:
#             # Ensure crm is a real user object
#             try:
#                 validated_data['crm'] = CustomUser.objects.get(id=crm_id.id if isinstance(crm_id, CustomUser) else crm_id)
#             except:
#                 validated_data['crm'] = request_user

#         user = CustomUser.objects.create_user(password=password, **validated_data)
#         return user

#     def update(self, instance, validated_data):
#         password = validated_data.pop('password', None)

#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)

#         if password and password.strip():
#             instance.set_password(password)

#         instance.save()
#         return instance




# # dealer form k liya
# class SSUserSerializerDealer(serializers.ModelSerializer):
#     crm_name = serializers.CharField(source="crm.name", read_only=True)
#     crm_user_id = serializers.CharField(source="crm.user_id", read_only=True)

#     class Meta:
#         model = CustomUser
#         fields = [
#             "id",
#             "user_id",
#             "name",
#             "party_name",
#             "mobile",
#             "role",
#             "crm_user_id",
#             "crm_name",
#         ]

# # dealer form k liya







from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken

from .models import CustomUser


# =========================================================
# SAFE USER SERIALIZER
# =========================================================

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "user_id",
            "mobile",
            "role",
            "stock_location",
            "name",
            "party_name",
            "crm",
            "ss",
            "is_active",
            "created_at",
            "created_by",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "created_at",
            "created_by",
        ]


# =========================================================
# CUSTOM JWT REFRESH SERIALIZER
# =========================================================

class CustomTokenRefreshSerializer(TokenRefreshSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.token

        user_id = refresh.get("user_id")
        token_auth_version = refresh.get("auth_version")

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            raise InvalidToken("User no longer exists.")

        # Account deactivated
        if not user.is_active:
            raise InvalidToken("Account is deactivated.")

        # Refresh token without auth_version
        if token_auth_version is None:
            raise InvalidToken("Session is no longer valid.")

        # Password/deactivation changed after this token was issued
        if int(token_auth_version) != user.auth_version:
            raise InvalidToken("Session is no longer valid.")

        return data


# =========================================================
# SS / DS / USER MANAGEMENT SERIALIZER
# =========================================================

class SSUserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True
    )

    crm_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser

        fields = [
            "id",
            "role",
            "user_id",
            "stock_location",
            "mobile",
            "password",
            "name",
            "crm",
            "crm_name",
            "ss",
            "party_name",
            "is_active",
            "created_at",
            "created_by",
        ]

        read_only_fields = [
            "id",
            "user_id",
            "created_at",
            "created_by",
            "crm_name",
        ]

    # -----------------------------------------------------
    # CRM NAME
    # -----------------------------------------------------

    def get_crm_name(self, obj):
        if obj.crm:
            return obj.crm.name or obj.crm.mobile
        return None

    # -----------------------------------------------------
    # MOBILE VALIDATION
    # -----------------------------------------------------

    def validate_mobile(self, value):

        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError(
                "Mobile number must be exactly 10 digits."
            )

        if CustomUser.objects.filter(
            mobile=value
        ).exclude(
            id=self.instance.id if self.instance else None
        ).exists():

            raise serializers.ValidationError(
                "This mobile number is already in use."
            )

        return value

    # -----------------------------------------------------
    # CREATE USER
    # -----------------------------------------------------

    def create(self, validated_data):

        request_user = self.context["request"].user

        password = validated_data.pop("password", None)

        if not password or not password.strip():
            raise serializers.ValidationError({
                "password": "Password is required."
            })

        # -------------------------------------------------
        # ROLE SECURITY
        # -------------------------------------------------

        role = validated_data.get("role") or "SS"

        # CRM must not be able to create privileged users
        if request_user.role == "CRM":
            allowed_roles = ["SS", "DS", "ASM"]

            if role not in allowed_roles:
                raise serializers.ValidationError({
                    "role": "CRM cannot create this user role."
                })

        # -------------------------------------------------
        # created_by ALWAYS SERVER CONTROLLED
        # -------------------------------------------------

        validated_data["created_by"] = request_user

        # -------------------------------------------------
        # CRM ASSIGNMENT
        # -------------------------------------------------

        crm_value = validated_data.get("crm")

        if request_user.role == "CRM":

            # CRM-created users always belong to this CRM
            validated_data["crm"] = request_user

        else:
            # ADMIN can assign a CRM
            if crm_value:

                if not isinstance(crm_value, CustomUser):
                    try:
                        crm_value = CustomUser.objects.get(
                            id=crm_value
                        )
                    except CustomUser.DoesNotExist:
                        raise serializers.ValidationError({
                            "crm": "Invalid CRM."
                        })

                if crm_value.role != "CRM":
                    raise serializers.ValidationError({
                        "crm": "Selected user is not a CRM."
                    })

                validated_data["crm"] = crm_value

            else:
                # Preserve existing behaviour:
                # if no CRM selected, use current user only
                if request_user.role == "CRM":
                    validated_data["crm"] = request_user

        # -------------------------------------------------
        # DS → SS VALIDATION
        # -------------------------------------------------

        ss_value = validated_data.get("ss")

        if role == "DS":

            if not ss_value:
                raise serializers.ValidationError({
                    "ss": "SS is required for DS."
                })

            if not isinstance(ss_value, CustomUser):
                try:
                    ss_value = CustomUser.objects.get(
                        id=ss_value
                    )
                except CustomUser.DoesNotExist:
                    raise serializers.ValidationError({
                        "ss": "Invalid SS."
                    })

            if ss_value.role != "SS":
                raise serializers.ValidationError({
                    "ss": "Selected user is not an SS."
                })

            # CRM can only assign its own SS
            if request_user.role == "CRM":
                if ss_value.crm_id != request_user.id:
                    raise serializers.ValidationError({
                        "ss": "You can only assign your own SS."
                    })

            validated_data["ss"] = ss_value

        # -------------------------------------------------
        # CREATE
        # -------------------------------------------------

        user = CustomUser.objects.create_user(
            password=password,
            **validated_data
        )

        return user

    # -----------------------------------------------------
    # UPDATE USER
    # -----------------------------------------------------

    def update(self, instance, validated_data):

        password = validated_data.pop("password", None)

        old_is_active = instance.is_active

        # -------------------------------------------------
        # SECURITY:
        # These fields must NEVER be changed through
        # normal user-management PATCH/PUT.
        # -------------------------------------------------

        validated_data.pop("created_by", None)

        # CRM cannot change ownership
        request_user = self.context["request"].user

        if request_user.role == "CRM":

            validated_data.pop("crm", None)

            # CRM cannot move a DS to another SS without
            # validation below
            new_ss = validated_data.get("ss")

            if new_ss:

                if not isinstance(new_ss, CustomUser):
                    try:
                        new_ss = CustomUser.objects.get(
                            id=new_ss
                        )
                    except CustomUser.DoesNotExist:
                        raise serializers.ValidationError({
                            "ss": "Invalid SS."
                        })

                if new_ss.role != "SS":
                    raise serializers.ValidationError({
                        "ss": "Selected user is not an SS."
                    })

                if new_ss.crm_id != request_user.id:
                    raise serializers.ValidationError({
                        "ss": "You can only assign your own SS."
                    })

                validated_data["ss"] = new_ss

        # -------------------------------------------------
        # ROLE SECURITY
        # -------------------------------------------------

        new_role = validated_data.get("role")

        if request_user.role == "CRM":

            if new_role is not None:
                allowed_roles = ["SS", "DS", "ASM"]

                if new_role not in allowed_roles:
                    raise serializers.ValidationError({
                        "role": "CRM cannot assign this user role."
                    })

        # -------------------------------------------------
        # APPLY NORMAL FIELDS
        # -------------------------------------------------

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # -------------------------------------------------
        # AUTH VERSION
        # -------------------------------------------------

        security_changed = False

        # Password changed
        if password and password.strip():

            instance.set_password(password)

            security_changed = True

        # Active/inactive status changed
        new_is_active = validated_data.get(
            "is_active",
            old_is_active
        )

        if new_is_active != old_is_active:

            security_changed = True

        # -------------------------------------------------
        # INVALIDATE ALL OLD TOKENS
        # -------------------------------------------------

        if security_changed:
            instance.auth_version += 1

        instance.save()

        return instance


# =========================================================
# DEALER FORM
# =========================================================

class SSUserSerializerDealer(serializers.ModelSerializer):

    crm_name = serializers.CharField(
        source="crm.name",
        read_only=True
    )

    crm_user_id = serializers.CharField(
        source="crm.user_id",
        read_only=True
    )

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