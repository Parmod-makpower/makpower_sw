from django.conf import settings
from django.db import transaction, connection
from .models import SamplingSheet, NotInStockReport, Mahotsav
from products.utils import get_sheet
from datetime import datetime

def sync_sampling_sheet():
    try:
        # 🔒 पुरानी DB connections बंद करो
        connection.close()

        sheet = get_sheet(
            sheet_id=settings.SHEET_ID_NEW,
            sheet_name="Sampling"
        )

        rows = sheet.get_all_records()

        with transaction.atomic():
            # ✅ पहले पूरा table clear
            SamplingSheet.objects.all().delete()

            if not rows:
                print("⚠️ Sampling sheet खाली है")
                return

            new_rows = []

            for row in rows:
                party_name = row.get("PARTY NAME")
                items = row.get("Items")
               
                if not party_name:
                    continue

                if not items or items.strip().lower() == "no":
                    items = ""

                new_rows.append(
                    SamplingSheet(
                        party_name=party_name.strip(),
                        items=items.strip(),
                    )
                )

            SamplingSheet.objects.bulk_create(new_rows)

        print(f"✅ Sampling sheet sync complete: {len(new_rows)} rows")

    except Exception as e:
        print(f"❌ Sync failed due to error: {e}")


def sync_not_in_stock():
    try:
        # 🔒 Close old DB connections
        connection.close()

        sheet = get_sheet(
            sheet_id=settings.SHEET_ID_NEW,
            sheet_name="NIS"
        )

        rows = sheet.get_all_records()

        if not rows:
            print("⚠️ NIS sheet खाली है")
            return

        objects = []

        with transaction.atomic():
            # 🗑️ Step 1: पहले पूरा table delete
            NotInStockReport.objects.all().delete()

            # 🔁 Step 2: Fresh data insert
            for row in rows:

                # 🔎 Skip if Valid Check = "No"
                valid_check = str(row.get("Valid check", "")).strip().lower()
                if valid_check == "no":
                    continue

                product = row.get("Item Name")
                original_qty = row.get("Original")
                date_value = row.get("Date")
                party_name = row.get("Party Name")
                order_no = row.get("Order No.")
                balance_qty = row.get("Balance qty")

                # ❌ Mandatory field check
                if not product or not party_name or not order_no:
                    continue

                # 📅 Date convert (sheet → Django)
                try:
                    date_value = datetime.strptime(str(date_value), "%d/%m/%Y").date()
                except Exception:
                    continue

                objects.append(
                    NotInStockReport(
                        product=product.strip(),
                        original_quantity=int(original_qty or 0),
                        date=date_value,
                        party_name=party_name.strip(),
                        order_no=order_no.strip(),
                        balance_qty=int(balance_qty or 0),
                    )
                )

            # 🚀 Bulk insert (Fast insertion)
            if objects:
                NotInStockReport.objects.bulk_create(objects, batch_size=1000)

        print(f"✅ Not In Stock sync complete: {len(objects)} rows inserted")

    except Exception as e:
        print(f"❌ NIS Sync failed: {e}")


def sync_mahotsav_sheet():
    try:
        connection.close()

        sheet = get_sheet(
            sheet_id=settings.SHEET_ID_NEW,
            sheet_name="MAHOTSAV_SHEET"
        )

        rows = sheet.get_all_records(expected_headers=[
            "crm_name",
            "product_name",
            "mahotsav_dispatch_quantity",
            "gas_stove",
            "kitchen_cookware",
            "dinner_set",
        ])

        with transaction.atomic():
            Mahotsav.objects.all().delete()

            if not rows:
                print("⚠️ Mahotsav sheet खाली है")
                return

            new_rows = []

            for row in rows:
                crm_name = row.get("crm_name", "")
                party_name = row.get("product_name", "")
                mahotsav_dispatch_quantity = row.get("mahotsav_dispatch_quantity")
                gas_stove = row.get("gas_stove")
                kitchen_cookware = row.get("kitchen_cookware")
                dinner_set = row.get("dinner_set")

                if not party_name:
                    continue

                new_rows.append(
                    Mahotsav(
                        crm_name=crm_name.strip() if crm_name else "",
                        party_name=party_name.strip(),
                        mahotsav_dispatch_quantity=mahotsav_dispatch_quantity,
                        gas_stove=gas_stove,
                        kitchen_cookware=kitchen_cookware,
                        dinner_set=dinner_set
                    )
                )

            Mahotsav.objects.bulk_create(new_rows)

        print(f"✅ Mahotsav sheet sync complete: {len(new_rows)} rows")

    except Exception as e:
        print(f"❌ Sync failed due to error: {e}")
