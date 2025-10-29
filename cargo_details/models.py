from django.db import models
from django.conf import settings

class CargoDetails(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cargo_details'
    )
    cargo_name = models.CharField(max_length=100)
    cargo_mobile_number = models.CharField(max_length=25)
    cargo_location = models.CharField(max_length=100)
    parcel_size = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cargo_name} - {self.user.party_name}"
