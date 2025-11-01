
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


def write_to_sheet(sheet_id, sheet_name, rows: list, retries=3, delay=5):
    """
    Efficiently write multiple rows to Google Sheet in a single API call.
    Auto-retries on temporary quota or network issues.
    """

    if not rows:
        logger.warning("⚠️ No rows to write to sheet.")
        return

    try:
        client = get_gspread_client()
        sheet = client.open_by_key(sheet_id).worksheet(sheet_name)

        # ✅ Find next available row
        existing_data = sheet.get_all_values()
        next_row = len(existing_data) + 1

        # ✅ Prepare range for bulk write (A-H = 8 columns here)
        last_col_letter = chr(ord("A") + len(rows[0]) - 1)
        range_str = f"A{next_row}:{last_col_letter}{next_row + len(rows) - 1}"

        for attempt in range(retries):
            try:
                # ✅ Single API call for all rows (fast + quota safe)
                sheet.update(range_str, rows)
                logger.info(f"✅ Successfully wrote {len(rows)} rows to sheet '{sheet_name}'")
                return
            except gspread.exceptions.APIError as e:
                if "quota" in str(e).lower() and attempt < retries - 1:
                    logger.warning(f"⚠️ Quota hit, retrying in {delay}s... (Attempt {attempt+1}/{retries})")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ Failed to write to sheet after {retries} retries: {e}")
                    raise e

    except Exception as e:
        logger.error(f"🚨 Error in write_to_sheet: {str(e)}", exc_info=True)
        raise e



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
