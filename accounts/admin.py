from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id','user_id', 'mobile', 'role', 'crm', 'ss', 'is_active']
