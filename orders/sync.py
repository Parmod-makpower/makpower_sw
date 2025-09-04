# dispatch_orders/sync.py
from django.conf import settings
from .models import DispatchOrder
from products.utils import get_sheet

def sync_dispatch_orders():
    try:
        sheet = get_sheet(sheet_id=settings.SHEET_ID_NEW, sheet_name="dispatch_orders")
        rows = sheet.get_all_records()

        if not rows:
            print("⚠️ Dispatch Orders sheet is empty.")
            return

        new_orders = []
        inserted = 0

        # ✅ Rows को reverse में चलाते हैं (नीचे से ऊपर)
        for row in reversed(rows):
            order_id = row.get("order_id")
            product = row.get("product")
            quantity = row.get("quantity")
            row_key = row.get("row_key")  # अब sheet से आएगा unique row_key

            if not row_key:
                continue  # अगर row_key missing है तो skip करो

            # अगर row_key पहले से DB में है → skip
            if DispatchOrder.objects.filter(row_key=row_key).exists():
                continue

            # नया order बनाओ
            new_orders.append(DispatchOrder(
                order_id=order_id,
                product=product,
                quantity=quantity,
                row_key=row_key
            ))
            inserted += 1

        # ✅ Bulk insert at once
        if new_orders:
            DispatchOrder.objects.bulk_create(new_orders[::-1])  # reverse ताकि सही order में जाएं

        print(f"✅ Sync complete: {inserted} new orders inserted.")

    except Exception as e:
        print(f"❌ DispatchOrder Sync failed: {e}")
