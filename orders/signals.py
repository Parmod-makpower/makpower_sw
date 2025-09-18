from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import SSOrder, SSOrderItem, PendingOrderItemSnapshot

@receiver(post_save, sender=SSOrderItem)
def create_pending_snapshot(sender, instance, **kwargs):
    order = instance.order
    if order.status == 'PENDING':
        PendingOrderItemSnapshot.objects.get_or_create(
            order=order,
            product=instance.product,
            defaults={'quantity': instance.quantity}
        )

@receiver(pre_delete, sender=SSOrder)
def delete_pending_snapshots(sender, instance, **kwargs):
    # If order deleted, clean up snapshot
    PendingOrderItemSnapshot.objects.filter(order=instance).delete()

@receiver(post_save, sender=SSOrder)
def remove_snapshot_on_status_change(sender, instance, **kwargs):
    if instance.status != 'PENDING':
        PendingOrderItemSnapshot.objects.filter(order=instance).delete()
