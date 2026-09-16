from django.db import models
from django.conf import settings


class ASMSSAssignment(models.Model):
    """
    Maps one SS to one ASM.

    Important:
    - An SS can have only ONE active ASM assignment.
    - Old/inactive assignments are preserved for history.
    - The same ASM + SS pair can be assigned again after deactivation.
    """

    asm = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asm_assignments",
        limit_choices_to={"role": "ASM"},
        db_index=True,
    )

    ss = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asm_assignments_received",
        limit_choices_to={"role": "SS"},
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

        # =====================================================
        # IMPORTANT:
        # Only ACTIVE ASM ↔ SS assignments must be unique.
        #
        # This allows:
        #
        # ASM1 → SS1 ACTIVE
        #        ↓ deactivate
        # ASM1 → SS1 INACTIVE
        #        ↓
        # ASM1 → SS1 ACTIVE again
        #
        # Old assignment remains in DB as history.
        # =====================================================
        constraints = [
            models.UniqueConstraint(
                fields=["asm", "ss"],
                condition=models.Q(is_active=True),
                name="unique_active_asm_ss_assignment",
            ),
        ]

        indexes = [
            models.Index(
                fields=["asm", "is_active"],
                name="asm_active_assignments_idx",
            ),
            models.Index(
                fields=["ss", "is_active"],
                name="ss_active_assignments_idx",
            ),
        ]

    def __str__(self):
        asm_name = (
            self.asm.name
            or self.asm.user_id
            or str(self.asm_id)
        )

        ss_name = (
            self.ss.name
            or self.ss.party_name
            or self.ss.user_id
            or str(self.ss_id)
        )

        status = "Active" if self.is_active else "Inactive"

        return f"{asm_name} → {ss_name} ({status})"