from django.contrib import admin
from .models import CargoDetails

@admin.register(CargoDetails)
class CargoDetailsAdmin(admin.ModelAdmin):
    list_display = ('cargo_name', 'cargo_mobile_number', 'cargo_location', 'parcel_size', 'get_party_name', 'created_at')

    def get_party_name(self, obj):
        return obj.user.party_name
    get_party_name.short_description = 'Party Name'
