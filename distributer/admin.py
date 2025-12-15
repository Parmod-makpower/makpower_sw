from django.contrib import admin
from .models import DSOrder, DSOrderItem
# Register your models here.

admin.site.register(DSOrder)
admin.site.register(DSOrderItem)