# models.py
from django.db import models

class SamplingSheet(models.Model):
    party_name = models.CharField(max_length=255)
    items = models.TextField(help_text="Comma separated item codes")

    def __str__(self):
        return self.party_name
    


class NotInStockReport(models.Model):
    product = models.CharField(max_length=200)
    original_quantity = models.PositiveIntegerField()
    date = models.DateField()
    party_name = models.CharField(max_length=255)
    order_no = models.CharField(max_length=100)
    balance_qty = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product} - {self.order_no}"
 

class PassportCouponRecord(models.Model):
    user_name = models.CharField(max_length=150)
    passport_number = models.CharField(max_length=50)
    coupon_number = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.user_name} - {self.passport_number}"