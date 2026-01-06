
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
from orders.models import PendingOrderItemSnapshot
from django.db.models import Sum
from google.oauth2.service_account import Credentials
import time
import logging
logger = logging.getLogger(__name__)


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



def get_gspread_client():
    """Authorize and return gspread client"""
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    return gspread.authorize(creds)

def write_to_sheet(sheet_id, sheet_name, rows: list, retries=3, delay=3):
    """
    Fast & safe bulk append to Google Sheet.
    No full sheet read → no timeout / quota issue.
    """

    if not rows:
        logger.warning("⚠️ No rows to write to sheet.")
        return

    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)

    for attempt in range(retries):
        try:
            # ✅ BEST way: direct append (Google handles row position)
            sheet.append_rows(rows, value_input_option="RAW")

            logger.info(f"✅ Successfully appended {len(rows)} rows to '{sheet_name}'")
            return

        except gspread.exceptions.APIError as e:
            err_msg = str(e).lower()

            if ("quota" in err_msg or "rate" in err_msg or "timeout" in err_msg) and attempt < retries - 1:
                logger.warning(
                    f"⚠️ Sheet API issue, retrying in {delay}s... "
                    f"(Attempt {attempt + 1}/{retries})"
                )
                time.sleep(delay)
            else:
                logger.error("❌ Sheet write failed permanently", exc_info=True)
                raise



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
