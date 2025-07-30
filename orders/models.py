# orders/models.py

from django.db import models
from django.conf import settings

class SSOrder(models.Model):
    order_id = models.CharField(max_length=30, unique=True)
    ss = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ss_orders')
    crm = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='crm_of_orders')
    party_name = models.CharField(max_length=150, blank=True, null=True)

    total_quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    placed_at = models.DateTimeField(auto_now_add=True)
    applied_schemes = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.order_id} (SS: {self.ss.user_id})"

class SSOrderItem(models.Model):
    order = models.ForeignKey(SSOrder, on_delete=models.CASCADE, related_name='items')
    product_id = models.CharField(max_length=100)
    sale_name = models.CharField(max_length=200, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_id} x {self.quantity}"
    
    
class CRMVerifiedOrder(models.Model):
    ss_order = models.OneToOneField(SSOrder, on_delete=models.CASCADE, related_name='verified_order')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_orders')

    total_quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('FORWARDED', 'Forwarded')], default='PENDING')
    notes = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Verified ({self.status}) - {self.ss_order.order_id}"

class CRMVerifiedOrderItem(models.Model):
    order = models.ForeignKey(CRMVerifiedOrder, on_delete=models.CASCADE, related_name='items')
    product_id = models.CharField(max_length=100)
    sale_name = models.CharField(max_length=200, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_id} x {self.quantity} (Verified)"

class CRMVerifiedOrderScheme(models.Model):
    order = models.ForeignKey(CRMVerifiedOrder, on_delete=models.CASCADE, related_name='verified_schemes')
    product_id = models.CharField(max_length=100)  # free product id
    sale_name = models.CharField(max_length=200, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    is_auto_applied = models.BooleanField(default=True)  # CRM can change it later

    def __str__(self):
        return f" {self.sale_name} ({self.product_id}) x {self.quantity}"
