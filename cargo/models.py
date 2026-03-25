from django.db import models
from accounts.models import CustomUser  # 👈 tera existing user model


class Cargo(models.Model):
    party = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="cargo_orders",
        limit_choices_to={"role": "SS"},
        db_index=True
    )

    cargo_name = models.CharField(max_length=150)
    parcel_size = models.CharField(max_length=50)
    cargo_location = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=15)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["party"], name="unique_party_cargo")
        ]
        
    def __str__(self):
        return f"{self.cargo_name} - {self.party.party_name}"