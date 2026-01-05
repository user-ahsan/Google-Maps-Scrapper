import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys
import datetime
import random

# Adjust path to find credentials in root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
SHEET_NAME = "Gmaps Leads"

def test_sheets():
    print("="*60)
    print("   GOOGLE SHEETS TEST   ")
    print("="*60)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Error: {CREDENTIALS_FILE} not found.")
        return

    print("1. Authenticating...")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        print("✅ Authenticated.")
    except Exception as e:
        print(f"❌ Authentication Failed: {e}")
        return

    print(f"2. Opening Sheet '{SHEET_NAME}'...")
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.sheet1
        print(f"✅ Sheet Open: {spreadsheet.title}")
    except Exception as e:
        print(f"❌ Failed to open sheet: {e}")
        # Try creating it? No, just fail for now as per user request to test connectivity
        return

    print("3. Writing Test Data...")
    test_msg = f"TEST_CONN_{random.randint(1000,9999)}"
    cell_loc = "Z1"
    try:
        worksheet.update_acell(cell_loc, test_msg)
        print(f"✅ Written '{test_msg}' to {cell_loc}")
    except Exception as e:
        print(f"❌ Write Failed: {e}")
        return

    print("4. Reading Test Data...")
    try:
        val = worksheet.acell(cell_loc).value
        print(f"   Read value: {val}")
        if val == test_msg:
            print("✅ Read Verification Successful")
        else:
            print("❌ Read Verification Mismatch")
    except Exception as e:
        print(f"❌ Read Failed: {e}")

    print("5. Deleting Test Data...")
    try:
        worksheet.update_acell(cell_loc, "")
        print("✅ Cell Cleared.")
    except Exception as e:
        print(f"❌ Delete Failed: {e}")

    print("="*60)
    print("🎉 SHEETS TEST COMPLETE")

if __name__ == "__main__":
    test_sheets()
