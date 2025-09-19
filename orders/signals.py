# orders/signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import SSOrder, SSOrderItem, PendingOrderItemSnapshot
from products.utils import recalculate_virtual_stock

@receiver(post_save, sender=SSOrderItem)
def create_pending_snapshot(sender, instance, created, **kwargs):
    order = instance.order
    if order.status == 'PENDING':
        snapshot, created_snap = PendingOrderItemSnapshot.objects.get_or_create(
            order=order,
            product=instance.product,
            defaults={'quantity': instance.quantity}
        )
        if not created_snap:
            snapshot.quantity = instance.quantity
            snapshot.save(update_fields=["quantity"])

        # ✅ Recalculate virtual stock
        recalculate_virtual_stock(instance.product)

@receiver(pre_delete, sender=SSOrder)
def delete_pending_snapshots(sender, instance, **kwargs):
    for snapshot in PendingOrderItemSnapshot.objects.filter(order=instance):
        recalculate_virtual_stock(snapshot.product)
    PendingOrderItemSnapshot.objects.filter(order=instance).delete()

@receiver(post_save, sender=SSOrder)
def remove_snapshot_on_status_change(sender, instance, **kwargs):
    if instance.status != 'PENDING':
        for snapshot in PendingOrderItemSnapshot.objects.filter(order=instance):
            recalculate_virtual_stock(snapshot.product)
        PendingOrderItemSnapshot.objects.filter(order=instance).delete()
