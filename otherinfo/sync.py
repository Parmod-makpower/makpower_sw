from django.conf import settings
from django.db import transaction, connection
from .models import SamplingSheet
from products.utils import get_sheet

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
                        items=items.strip()
                    )
                )

            SamplingSheet.objects.bulk_create(new_rows)

        print(f"✅ Sampling sheet sync complete: {len(new_rows)} rows")

    except Exception as e:
        print(f"❌ Sync failed due to error: {e}")
