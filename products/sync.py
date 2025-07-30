from django.conf import settings
from django.db import transaction
from .models import Product
from .utils import get_sheet

def sheet_to_db():
    sheet = get_sheet(sheet_id=settings.SHEET_ID_NEW)
    rows = sheet.get_all_records()

    with transaction.atomic():
        # Step 1: Delete all old data
        Product.objects.all().delete()

        # Step 2: Prepare new data
        products = []
        for row in rows:
            product = Product(
                product_id=row.get('product_id'),
                product_name=row.get('product_name'),
                category=row.get('category'),
                sale_name=row.get('sale_name'),
                live_stock=row.get('live_stock'),
                cartoon_size=row.get('cartoon_size'),
                price=row.get('price')
            )
            products.append(product)

        # Step 3: Bulk insert
        Product.objects.bulk_create(products)

    print(f"✅ Inserted {len(products)} products from Google Sheet after clean delete.")
