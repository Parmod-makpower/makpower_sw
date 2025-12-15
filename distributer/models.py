from django.db import models
from django.conf import settings
from products.models import Product

import uuid

class DSOrder(models.Model):
    ds_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ds_orders', db_index=True)
    order_id = models.CharField(max_length=20, unique=True, editable=False , null=True, blank=True)  # 🔑 unique order id
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='PENDING')

    note = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.order_id:
            # Example format: ORD-ABC12345
            self.order_id = "ORD-" + uuid.uuid4().hex[:7].upper()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.order_id} - {self.total_amount}"

class DSOrderItem(models.Model):
    order = models.ForeignKey(DSOrder, on_delete=models.CASCADE, related_name='items',db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_index=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    ds_virtual_stock = models.PositiveIntegerField(default=0)
    is_scheme_item = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product} - {self.quantity}"

