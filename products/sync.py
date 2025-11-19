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

        updated_live = 0
        updated_mumbai = 0

        with transaction.atomic():
            for row in rows:
                product_id = row.get("product_id")
                if not product_id:
                    continue

                try:
                    product = Product.objects.get(product_id=product_id)

                    # ------------------------------------------------
                    # 1️⃣ LIVE STOCK SYNC (same as your old logic)
                    # ------------------------------------------------
                    live_stock_from_sheet = row.get("live_stock")

                    if live_stock_from_sheet not in [None, '', ' ']:
                        try:
                            live_stock_from_sheet = int(live_stock_from_sheet)
                        except ValueError:
                            print(f"⚠️ Invalid live_stock for product {product_id}: {live_stock_from_sheet}")
                            live_stock_from_sheet = None

                        if live_stock_from_sheet is not None:
                            if product.live_stock != live_stock_from_sheet:
                                product.live_stock = live_stock_from_sheet
                                product.save(update_fields=["live_stock"])

                                # Recalculate virtual stock only for live_stock change
                                recalculate_virtual_stock(product)

                                updated_live += 1

                    # ------------------------------------------------
                    # 2️⃣ MUMBAI STOCK SYNC (SAFE + BUG-FREE)
                    # ------------------------------------------------
                    if "mumbai_stock" in row and row["mumbai_stock"] not in [None, '', ' ', 0]:
                        mumbai_stock_from_sheet = row["mumbai_stock"]

                        try:
                            mumbai_stock_from_sheet = int(mumbai_stock_from_sheet)
                        except ValueError:
                            print(f"⚠️ Invalid mumbai_stock for product {product_id}: {mumbai_stock_from_sheet}")
                            mumbai_stock_from_sheet = None

                        if mumbai_stock_from_sheet is not None:
                            if product.mumbai_stock != mumbai_stock_from_sheet:
                                product.mumbai_stock = mumbai_stock_from_sheet
                                product.save(update_fields=["mumbai_stock"])

                                # NO virtual stock recalc here
                                updated_mumbai += 1

                    else:
                        # Mumbai stock missing/blank/null → ignore safely
                        pass

                except Product.DoesNotExist:
                    continue

        print(f"✅ Sync complete: {updated_live} live stock updated & virtual stock recalculated.")
        print(f"✅ Mumbai stock updated for {updated_mumbai} products.")

    except Exception as e:
        print(f"❌ Sync failed due to error: {e}")
