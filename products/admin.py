from django.contrib import admin
from .models import  Product, SaleName, Scheme, SchemeCondition, SchemeReward

admin.site.register(Product)
admin.site.register(SaleName)
admin.site.register(Scheme)
admin.site.register(SchemeCondition)
admin.site.register(SchemeReward)