from rest_framework import serializers

from accounts.models import CustomUser
from .models import ASMSSAssignment


class ASMSSAssignmentSerializer(serializers.ModelSerializer):
    asm_name = serializers.CharField(
        source="asm.name",
        read_only=True,
    )
    asm_user_id = serializers.CharField(
        source="asm.user_id",
        read_only=True,
    )

    ss_name = serializers.CharField(
        source="ss.name",
        read_only=True,
    )
    ss_party_name = serializers.CharField(
        source="ss.party_name",
        read_only=True,
    )
    ss_user_id = serializers.CharField(
        source="ss.user_id",
        read_only=True,
    )
    ss_mobile = serializers.CharField(
        source="ss.mobile",
        read_only=True,
    )

    class Meta:
        model = ASMSSAssignment
        fields = [
            "id",
            "asm",
            "asm_name",
            "asm_user_id",
            "ss",
            "ss_name",
            "ss_party_name",
            "ss_user_id",
            "ss_mobile",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "asm_name",
            "asm_user_id",
            "ss_name",
            "ss_party_name",
            "ss_user_id",
            "ss_mobile",
            "created_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")

        asm = attrs.get("asm")
        ss = attrs.get("ss")

        if not asm:
            raise serializers.ValidationError({
                "asm": "ASM is required."
            })

        if not ss:
            raise serializers.ValidationError({
                "ss": "SS is required."
            })

        # -----------------------------------------
        # ROLE VALIDATION
        # -----------------------------------------

        if asm.role != "ASM":
            raise serializers.ValidationError({
                "asm": "Selected user is not an ASM."
            })

        if ss.role != "SS":
            raise serializers.ValidationError({
                "ss": "Selected user is not an SS."
            })

        if not asm.is_active:
            raise serializers.ValidationError({
                "asm": "Selected ASM is inactive."
            })

        if not ss.is_active:
            raise serializers.ValidationError({
                "ss": "Selected SS is inactive."
            })

        # -----------------------------------------
        # CRM OWNERSHIP VALIDATION
        # -----------------------------------------

        if request and request.user.role == "CRM":

            if ss.crm_id != request.user.id:
                raise serializers.ValidationError({
                    "ss": "You can only assign your own SS users."
                })

            # ASM created by another CRM should not be
            # assignable by this CRM.
            if asm.created_by_id != request.user.id:
                raise serializers.ValidationError({
                    "asm": "You can only assign an ASM created by your CRM."
                })

        # -----------------------------------------
        # ACTIVE ASSIGNMENT VALIDATION
        # -----------------------------------------

        instance = self.instance

        existing = ASMSSAssignment.objects.filter(
            ss=ss,
            is_active=True,
        )

        if instance:
            existing = existing.exclude(id=instance.id)

        if existing.exists():
            current = existing.select_related("asm").first()

            raise serializers.ValidationError({
                "ss": (
                    f"This SS is already assigned to "
                    f"{current.asm.name or current.asm.user_id}."
                )
            })

        return attrs


class ASMSSAssignmentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for ASM dashboard.
    Used when we only need assigned SS information.
    """

    ss_name = serializers.CharField(
        source="ss.name",
        read_only=True,
    )
    ss_party_name = serializers.CharField(
        source="ss.party_name",
        read_only=True,
    )
    ss_user_id = serializers.CharField(
        source="ss.user_id",
        read_only=True,
    )
    ss_mobile = serializers.CharField(
        source="ss.mobile",
        read_only=True,
    )

    class Meta:
        model = ASMSSAssignment
        fields = [
            "id",
            "ss",
            "ss_name",
            "ss_party_name",
            "ss_user_id",
            "ss_mobile",
            "created_at",
        ]