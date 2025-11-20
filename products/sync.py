from django.conf import settings
from django.db import transaction
from .models import Product
from .utils import get_sheet, recalculate_virtual_stock


def clean_stock_value(value):
    """
    Normalizes stock values coming from Google Sheet.
    - Blank / None / '0' / ' 0 ' -> 0
    - Valid numbers -> int
    - Invalid entries -> None
    """
    if value in [None, '', ' ', '0', 0, '0 ', ' 0', ' 0 ']:
        return 0

    try:
        return int(value)
    except Exception:
        return None


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
                    continue

                try:
                    product = Product.objects.get(product_id=product_id)
                except Product.DoesNotExist:
                    continue

                # ---------------------------
                # 🔥 1) LIVE STOCK SYNC
                # ---------------------------
                live_stock_from_sheet = row.get("live_stock")

                # Clean the value
                live_stock_clean = clean_stock_value(live_stock_from_sheet)

                if live_stock_clean is not None and product.live_stock != live_stock_clean:
                    product.live_stock = live_stock_clean
                    product.save(update_fields=["live_stock"])
                    recalculate_virtual_stock(product)
                    updated += 1

                # ---------------------------
                # 🔥 2) MUMBAI STOCK SYNC
                # ---------------------------
                mumbai_stock_from_sheet = row.get("mumbai_stock")

                # Clean the value
                mumbai_stock_clean = clean_stock_value(mumbai_stock_from_sheet)

                if mumbai_stock_clean is not None and product.mumbai_stock != mumbai_stock_clean:
                    product.mumbai_stock = mumbai_stock_clean
                    product.save(update_fields=["mumbai_stock"])
                    updated += 1

        print(f"✅ Synced: {updated} products updated (live + mumbai stock).")

    except Exception as e:
        print(f"❌ Sync failed due to error: {e}")
