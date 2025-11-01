# products/sync.py
from django.conf import settings
from django.db import transaction
from .models import Product
from .utils import get_sheet, recalculate_virtual_stock

def sheet_to_db():
    try:
        sheet = get_sheet(sheet_id=settings.SHEET_ID_NEW)
        rows = sheet.get_all_records()

        if not rows:
            print("⚠️ Sheet is empty — no data to sync.")
            return

        updated = 0

        with transaction.atomic():
            for row in rows:
                product_id = row.get("product_id")
                if not product_id:
                    continue  # Skip rows without product_id

                try:
                    product = Product.objects.get(product_id=product_id)
                    live_stock_from_sheet = row.get("live_stock")

                    # ✅ Convert to number safely
                    if live_stock_from_sheet in [None, '', ' ']:
                        continue  # skip if empty
                    try:
                        live_stock_from_sheet = int(live_stock_from_sheet)
                    except ValueError:
                        print(f"⚠️ Invalid live_stock for product {product_id}: {live_stock_from_sheet}")
                        continue

                    # ✅ Update only if changed
                    if product.live_stock != live_stock_from_sheet:
                        product.live_stock = live_stock_from_sheet
                        product.save(update_fields=["live_stock"])

                        # ✅ Recalculate virtual_stock immediately
                        recalculate_virtual_stock(product)

                        updated += 1

                except Product.DoesNotExist:
                    continue

        print(f"✅ Synced: {updated} products updated & virtual stock recalculated.")

    except Exception as e:
        print(f"❌ Sync failed due to error: {e}")
