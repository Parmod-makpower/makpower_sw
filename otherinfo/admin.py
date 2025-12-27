from django.contrib import admin
from .models import SamplingSheet, NotInStockReport, PassportCouponRecord
# Register your models here.

admin.site.register(SamplingSheet)
admin.site.register(NotInStockReport)
admin.site.register(PassportCouponRecord)
