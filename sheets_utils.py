import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd
import datetime
import glob

# --- Configuration ---
SHEET_NAME = "Gmaps Leads"  # The Google Sheet to save results to
CREDENTIALS_FILE = "credentials.json"

# Strict Schema Definition
EXPECTED_HEADERS = [
    "Name", "Address", "Domain", "Website", "Phone Number", 
    "Category", "Location", "Reviews Count", "Reviews Average", 
    "Latitude", "Longitude", "Google Maps Link", 
    "Scraped Query", "Scraped At"
]

# Internal logic keys to default display names
DEFAULT_MAPPING = {
    "name": "Name",
    "address": "Address",
    "domain": "Domain",
    "website": "Website",
    "phone_number": "Phone Number",
    "category": "Category",
    "location": "Location",
    "reviews_count": "Reviews Count",
    "reviews_average": "Reviews Average",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "google_maps_link": "Google Maps Link",
    "scraped_query": "Scraped Query",
    "scraped_at": "Scraped At"
}

def connect_to_sheets(credentials_file=CREDENTIALS_FILE):
    """Connects to Google Sheets using credentials.json"""
    if not os.path.exists(credentials_file):
        print(f"Error: {credentials_file} not found. Please place your Google Service Account credentials in the project root.")
        return None

    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error connecting to sheets: {e}")
        return None

def get_or_create_worksheet(client, sheet_name=SHEET_NAME, worksheet_title="Sheet1"):
    """Gets a worksheet by title, or creates it if it doesn't exist."""
    try:
        spreadsheet = client.open(sheet_name)
        try:
            worksheet = spreadsheet.worksheet(worksheet_title)
            return worksheet
        except gspread.WorksheetNotFound:
            return spreadsheet.add_worksheet(title=worksheet_title, rows=1000, cols=20)
    except Exception as e:
        print(f"Error opening sheet: {e}")
        return None

def generate_unique_key(row_data):
    """
    Generates a unique key for a business based on Name and Phone (or Address/Website).
    Handles both dictionary (row_data) and pandas Series.
    """
    # Normalize input to dict-like access
    name = str(row_data.get('Name', '') or row_data.get('name', '')).strip().lower()
    phone = str(row_data.get('Phone Number', '') or row_data.get('phone_number', '')).strip()
    address = str(row_data.get('Address', '') or row_data.get('address', '')).strip().lower()
    
    # Primary Key: Name + Phone
    if phone and phone != "No Phone":
        return f"{name}|{phone}"
    
    # Secondary Key: Name + Address (if phone is missing)
    if address:
        return f"{name}|{address}"
        
    # Fallback: Just Name (weakest, but better than nothing)
    return name

def get_existing_keys(worksheet):
    """
    Fetches all data from the worksheet and creates a set of unique keys for existing records.
    Uses get_all_values() to avoid errors with duplicate headers.
    """
    try:
        # Use get_all_values instead of get_all_records to handle duplicate headers safely
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            return set()
        
        headers = all_values[0]
        data_rows = all_values[1:]
        
        # Helper to find index safely
        def get_col_index(name_variations):
            for name in name_variations:
                if name in headers:
                    return headers.index(name)
            return -1

        name_idx = get_col_index(['Name', 'name'])
        phone_idx = get_col_index(['Phone Number', 'phone_number', 'Phone'])
        address_idx = get_col_index(['Address', 'address'])

        existing_keys = set()
        for row in data_rows:
            # Ensure row has enough columns
            row_data = {}
            if name_idx != -1 and name_idx < len(row): row_data['Name'] = row[name_idx]
            if phone_idx != -1 and phone_idx < len(row): row_data['Phone Number'] = row[phone_idx]
            if address_idx != -1 and address_idx < len(row): row_data['Address'] = row[address_idx]
            
            key = generate_unique_key(row_data)
            if key:
                existing_keys.add(key)
        
        return existing_keys
    except Exception as e:
        print(f"   -> Warning: Could not fetch existing data. Error: {e}")
        return set()

def map_columns_to_sheet(df, worksheet):
    """
    Aligns the DataFrame columns to match the existing Google Sheet headers.
    Dynamically maps internal field names to Sheet headers using aliases.
    If the sheet is empty, sets default headers.
    """
    
    try:
        # Get existing headers from the sheet
        existing_headers = worksheet.row_values(1)
    except:
        existing_headers = []

    if not existing_headers:
        # Sheet is empty, use REQUIRED headers
        print("   -> Sheet is empty. Setting up strict headers...")
        worksheet.append_row(EXPECTED_HEADERS)
        existing_headers = EXPECTED_HEADERS

    # We map internal keys to the Sheet's headers. 
    # Current strict requirement: Sheet MUST follow EXPECTED_HEADERS or we try to force it.
    
    # Check if existing headers match expected (approximated)
    # If they differ significantly, we might have issues, but we'll try to map what we can.
    
    # 1. Rename internal columns to Display Names
    rename_map = {}
    for internal, display in DEFAULT_MAPPING.items():
        rename_map[internal] = display
    
    # Apply aliases if needed (though we want to stick to DEFAULT_MAPPING mostly now)
    # The previous dynamic logic is good for robustness, but user wants strict columns.
    # Let's trust DEFAULT_MAPPING which aligns with EXPECTED_HEADERS.
    
    df = df.rename(columns=rename_map)

    # 2. Ensure ALL Expected Headers exist
    for h in EXPECTED_HEADERS:
        if h not in df.columns:
            df[h] = ""
            
    # 3. Select ONLY Expected Headers in Order
    final_df = df[EXPECTED_HEADERS].copy()
    
    return final_df

    return final_df

def upload_data_to_sheet(worksheet, df_new):
    """
    Handles the deduplication and upload of data provided in df_new.
    Returns logic summary (added, duplicate).
    """
    
    # 1. Fetch Existing Keys
    print("   Checking for duplicates...")
    existing_keys = get_existing_keys(worksheet)
    
    # 2. Map Columns (standardize to sheet)
    df_mapped = map_columns_to_sheet(df_new, worksheet)
    
    # 3. Filter Duplicates
    initial_count = len(df_mapped)
    new_rows = []
    
    for index, row in df_mapped.iterrows():
        key = generate_unique_key(row)
        if key not in existing_keys:
            new_rows.append(row)
            existing_keys.add(key) # Add to local set to prevent dupes within same batch
    
    if not new_rows:
        return 0, initial_count
    
    # 4. Prepare for Upload
    df_final = pd.DataFrame(new_rows)
    df_final = df_final.fillna("")
    
    # Escape Phone Numbers
    for col in df_final.columns:
        if any(x in str(col).lower() for x in ['phone', 'mobile', 'tel']):
                df_final[col] = df_final[col].apply(lambda x: f"'{x}" if str(x).strip().startswith('+') else x)

    data_to_upload = df_final.values.tolist()
    
    # 5. Upload
    try:
        col_a_values = worksheet.col_values(1)
        next_row = len(col_a_values) + 1
        range_name = f"A{next_row}"
        
        print(f"   Writing data starting at cell {range_name}...")
        worksheet.update(range_name=range_name, values=data_to_upload, value_input_option='USER_ENTERED')
        return len(new_rows), initial_count - len(new_rows)
    except Exception as ex:
        print(f"   -> Error writing to sheet: {ex}")
        # Fallback
        worksheet.append_rows(data_to_upload, value_input_option='USER_ENTERED')
        return len(new_rows), initial_count - len(new_rows)

def get_all_seen_urls(worksheet=None, local_dir='GMaps Data'):
    """
    aggregates all Google Maps Links from:
    1. The provided Google Sheet worksheet (if online)
    2. All local CSV files in the data directory
    Returns a set of unique URLs.
    """
    seen_urls = set()
    
    # 1. From Sheets
    if worksheet:
        try:
            print("   Fetching existing URLs from Google Sheets...", end=" ")
            # Find the 'Google Maps Link' column index
            # We assume header is in row 1
            headers = worksheet.row_values(1)
            link_col_idx = -1
            
            # Try to find the column dynamically
            candidates = ['Google Maps Link', 'google_maps_link', 'Link', 'Url']
            for i, h in enumerate(headers):
                if h in candidates:
                    link_col_idx = i + 1 # 1-based index for col_values
                    break
            
            if link_col_idx != -1:
                urls = worksheet.col_values(link_col_idx)
                # Remove header from list if it matches
                if urls and urls[0] in candidates:
                    urls = urls[1:]
                
                count_before = len(seen_urls)
                for u in urls:
                    if u and isinstance(u, str) and u.strip():
                        seen_urls.add(u.strip())
                print(f"Done. Found {len(seen_urls) - count_before} unique online.")
            else:
                print("Warning: 'Google Maps Link' column not found in Sheet.")
        except Exception as e:
            print(f"Error reading from sheet: {e}")

    # 2. From Local CSVs
    if os.path.exists(local_dir):
        print("   Scanning local data for URLs...", end=" ")
        # Prioritize correct file, but scan all for robustness
        csv_files = glob.glob(os.path.join(local_dir, '**', '*.csv'), recursive=True)
        count_before = len(seen_urls)
        
        for csv_path in csv_files:
            try:
                # Read only that column
                # We know the column name "Google Maps Link" from strict schema
                df = pd.read_csv(csv_path)
                
                # Check for likely column names
                target_col = None
                for col in df.columns:
                    if col in ['Google Maps Link', 'google_maps_link']:
                        target_col = col
                        break
                
                if target_col:
                     for u in df[target_col].dropna():
                         if isinstance(u, str) and u.strip():
                             seen_urls.add(u.strip())
            except Exception:
                pass
        print(f"Done. Total unique (Online + Offline): {len(seen_urls)}")
    
    return seen_urls
