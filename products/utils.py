
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings

def get_sheet(sheet_id=None, sheet_name="live_stock_sheet"):
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_CREDS, scope)
    client = gspread.authorize(creds)
    
    sheet_id = sheet_id or settings.SHEET_ID
    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    return sheet


# products/utils.py
from orders.models import PendingOrderItemSnapshot
from django.db.models import Sum

def recalculate_virtual_stock(product, save=True):
    """
    Recalculate virtual_stock for a single Product instance.
    - If live_stock is None -> virtual_stock will be set to None.
    - Else -> virtual_stock = max(live_stock - pending_qty, 0)
    Returns the computed value (None or int).
    """
    pending_qty = PendingOrderItemSnapshot.objects.filter(product=product).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    if product.live_stock is None:
        vs = None
    else:
        vs = product.live_stock - pending_qty
        if vs < 0:
            vs = 0

    product.virtual_stock = vs
    if save:
        product.save(update_fields=["virtual_stock"])
    return vs
