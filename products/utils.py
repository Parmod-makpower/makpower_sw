import os
import json
import time
import logging
import gspread
from django.conf import settings
from django.db.models import Sum
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials
from orders.models import PendingOrderItemSnapshot

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------------
# 🔹 Universal Google Sheets Client (Works on Local & Live)
# -----------------------------------------------------------------------------------

def get_gspread_client():
    """
    Authorize and return gspread client.
    ✅ Works both locally (credentials.json) and on Render/live (GOOGLE_CREDS_JSON env var)
    """
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = None

    # 🖥️ Local: credentials.json file exists
    if os.path.exists("credentials.json"):
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)

    # ☁️ Live: GOOGLE_CREDS_JSON environment variable
    elif os.environ.get("GOOGLE_CREDS_JSON"):
        creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

    # ❌ If nothing found
    else:
        raise Exception("❌ No Google credentials found. Please set GOOGLE_CREDS_JSON or upload credentials.json")

    return gspread.authorize(creds)


# -----------------------------------------------------------------------------------
# 🔹 Read Data from Google Sheet
# -----------------------------------------------------------------------------------

def get_sheet(sheet_id=None, sheet_name="live_stock_sheet"):
    """
    Returns a Google Sheet worksheet object.
    Uses either GOOGLE_CREDS_JSON or local credentials.json automatically.
    """
    try:
        client = get_gspread_client()
        sheet_id = sheet_id or getattr(settings, "SHEET_ID", None)
        if not sheet_id:
            raise Exception("⚠️ SHEET_ID not found in settings or argument")

        sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
        return sheet

    except Exception as e:
        logger.error(f"🚨 Error in get_sheet: {e}", exc_info=True)
        raise e


# -----------------------------------------------------------------------------------
# 🔹 Write Multiple Rows to Sheet
# -----------------------------------------------------------------------------------

def write_to_sheet(sheet_id, sheet_name, rows: list, retries=3, delay=5):
    """
    Efficiently write multiple rows to Google Sheet in one API call.
    Automatically retries on temporary quota or network errors.
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

        # ✅ Prepare range for bulk write (A-H = 8 columns)
        last_col_letter = chr(ord("A") + len(rows[0]) - 1)
        range_str = f"A{next_row}:{last_col_letter}{next_row + len(rows) - 1}"

        for attempt in range(retries):
            try:
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
        logger.error(f"🚨 Error in write_to_sheet: {e}", exc_info=True)
        raise e


# -----------------------------------------------------------------------------------
# 🔹 Virtual Stock Calculation
# -----------------------------------------------------------------------------------

def recalculate_virtual_stock(product, save=True):
    """
    Recalculate virtual_stock for a single Product instance.

    Logic:
    - If live_stock is None → virtual_stock = None
    - Else → virtual_stock = max(live_stock - pending_qty, 0)
    """

    try:
        pending_qty = PendingOrderItemSnapshot.objects.filter(product=product).aggregate(
            total=Sum("quantity")
        )["total"] or 0

        if product.live_stock is None:
            vs = None
        else:
            vs = max(product.live_stock - pending_qty, 0)

        product.virtual_stock = vs
        if save:
            product.save(update_fields=["virtual_stock"])

        return vs

    except Exception as e:
        logger.error(f"🚨 Error recalculating virtual stock for product {product.id}: {e}", exc_info=True)
        raise e
