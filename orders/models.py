from django.db import models
from django.conf import settings
from products.models import Product

import uuid

class SSOrder(models.Model):
    ss_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ss_orders', db_index=True)
    assigned_crm = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_orders', db_index=True)
    order_id = models.CharField(max_length=20, unique=True, editable=False , null=True, blank=True)  # 🔑 unique order id
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='PENDING')

    note = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.order_id:
            # Example format: ORD-ABC12345
            self.order_id = "ORD-" + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.order_id} - {self.total_amount}"

class SSOrderItem(models.Model):
    order = models.ForeignKey(SSOrder, on_delete=models.CASCADE, related_name='items',db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_index=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    ss_virtual_stock = models.PositiveIntegerField(default=0)
    is_scheme_item = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product} - {self.quantity}"


# orders/models.py

class CRMVerifiedOrder(models.Model):
    original_order = models.ForeignKey(SSOrder, on_delete=models.CASCADE, related_name="crm_verified_versions", db_index=True)
    crm_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verified_orders", db_index=True)
    verified_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('HOLD', 'Hold')],
        db_index=True,
        )
    notes = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    punched = models.BooleanField(default=False, db_index=True)
    dispatch_location = models.CharField(max_length=50, default="Delhi", db_index=True)  # 🆕 Added



    class Meta:
        indexes = [
            models.Index(fields=["crm_user", "verified_at"]),
            models.Index(fields=["original_order", "verified_at"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-verified_at"]

    def __str__(self):
        return f"{self.original_order} - {self.total_amount}"


class CRMVerifiedOrderItem(models.Model):
    crm_order = models.ForeignKey(CRMVerifiedOrder, on_delete=models.CASCADE, related_name='items', db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_index=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    ss_virtual_stock = models.PositiveIntegerField(default=0)
    is_rejected = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.product} - {self.quantity}"


class DispatchOrder(models.Model):
    row_key = models.CharField(max_length=100, unique=True)
    product = models.CharField(max_length=30)  
    quantity = models.PositiveIntegerField()
    order_id = models.CharField(max_length=20, db_index=True)  



class PendingOrderItemSnapshot(models.Model):
    order = models.ForeignKey(SSOrder, on_delete=models.CASCADE, related_name='pending_snapshots', db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_id} - {self.product}- {self.product.product_name} - {self.quantity}"
