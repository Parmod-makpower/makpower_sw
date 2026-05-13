from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from orders.models import SSOrder, PendingOrderItemSnapshot
from products.utils import recalculate_virtual_stock


def auto_hold_old_orders():

    print("Checking old pending orders...")

    old_orders = SSOrder.objects.filter(
        status="PENDING",
        created_at__lte=timezone.now() - timedelta(days=4)
    )

    for order in old_orders:

        try:
            with transaction.atomic():

                snapshots = PendingOrderItemSnapshot.objects.filter(order=order)

                affected_products = [
                    snap.product for snap in snapshots
                ]

                # ✅ snapshots delete
                snapshots.delete()

                # ✅ stock restore
                for product in set(affected_products):
                    recalculate_virtual_stock(product)

                # ✅ HOLD
                order.status = "HOLD"
                order.notes = "Auto HOLD after 3 days"
                order.save()

                print(f"{order.order_id} moved to HOLD")

        except Exception as e:
            print("ERROR:", e)