from django.conf import settings
from django.db import transaction
from .models import Product
from .utils import get_sheet

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

                    # Only update if value is different
                    if product.live_stock != live_stock_from_sheet:
                        product.live_stock = live_stock_from_sheet
                        product.save(update_fields=["live_stock"])
                        updated += 1

                except Product.DoesNotExist:
                    # Skip if product not found
                    continue

        print(f"✅ Synced: {updated} products updated.")

    except Exception as e:
        print(f"❌ Sync failed due to error: {e}")
