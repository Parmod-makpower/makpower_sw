from django.db import models

class Product(models.Model):
    product_id = models.CharField(max_length=20,null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    product_name = models.CharField(max_length=50, null=True, blank=True)
    sale_name = models.CharField(max_length=50, null=True, blank=True)
    live_stock = models.CharField(max_length=50, null=True, blank=True)
    cartoon_size = models.CharField(max_length=50, null=True, blank=True)
    price = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return f"{self.sale_name} - {self.product_name}"


class Scheme(models.Model):
    SCHEME_TYPE_CHOICES = [
        ('single', 'Single'),
        ('combo', 'Combo'),
    ]

    scheme_name = models.CharField(max_length=100)
    scheme_type = models.CharField(max_length=10, choices=SCHEME_TYPE_CHOICES)
    conditions = models.JSONField(help_text="List of required product IDs and quantities")
    rewards = models.JSONField(help_text="List of free product IDs and quantities")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.scheme_name
