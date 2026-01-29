# models.py
from django.db import models

class SamplingSheet(models.Model):
    party_name = models.CharField(max_length=255)
    items = models.TextField(help_text="Comma separated item codes")
    mahotsav_dispatch_quantity = models.CharField(max_length=200, null=True, blank=True)

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
 

class Mahotsav(models.Model):
    crm_name = models.CharField(max_length=100)
    party_name = models.CharField(max_length=255)
    mahotsav_dispatch_quantity = models.CharField(max_length=200, null=True, blank=True)
    gas_stove = models.CharField(max_length=10, null=True, blank=True)
    kitchen_cookware = models.CharField(max_length=10, null=True, blank=True)
    dinner_set = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.party_name