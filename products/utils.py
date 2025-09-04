
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
