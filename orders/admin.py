from django.contrib import admin
from .models import SSOrder, SSOrderItem, CRMVerifiedOrder, CRMVerifiedOrderItem, DispatchOrder

admin.site.register(SSOrder)
admin.site.register(SSOrderItem)
admin.site.register(CRMVerifiedOrder)
admin.site.register(CRMVerifiedOrderItem)
admin.site.register(DispatchOrder)
