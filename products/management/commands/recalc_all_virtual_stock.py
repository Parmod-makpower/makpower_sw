# products/management/commands/recalc_all_virtual_stock.py
from django.core.management.base import BaseCommand
from products.models import Product
from products.utils import recalculate_virtual_stock

class Command(BaseCommand):
    help = "Recalculate virtual_stock for all products"

    def handle(self, *args, **options):
        qs = Product.objects.all()
        total = qs.count()
        updated = 0
        for p in qs.iterator():
            old = p.virtual_stock
            new = recalculate_virtual_stock(p, save=True)
            if old != new:
                updated += 1
                self.stdout.write(f"Updated {p.product_id}: {old} -> {new}")
        self.stdout.write(self.style.SUCCESS(f"{updated}/{total} products updated."))
