# Made by user-ahsan
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd
import datetime
import glob
import re
from dataclasses import dataclass, asdict, field
from typing import Optional

class TimeoutError(Exception):
    pass

# --- Configuration ---
SHEET_NAME = "Gmaps Leads"  # The Google Sheet to save results to
CREDENTIALS_FILE = "credentials.json"

# --- Text Cleaning Utilities ---

def remove_emojis(text):
    """
    Remove emoji and special Unicode characters from text.
    Preserves normal text, numbers, and standard punctuation.
    """
    if not text or not isinstance(text, str):
        return text
    
    # Comprehensive emoji pattern covering all Unicode emoji ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002500-\U00002BEF"  # chinese char
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642" 
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+", 
        flags=re.UNICODE
    )
    
    return emoji_pattern.sub(r'', text).strip()

def clean_text_for_csv(text):
    """
    Clean text for safe CSV export:
    - Remove emojis
    - Remove excessive whitespace
    - Remove newlines and carriage returns
    - Trim leading/trailing whitespace
    """
    if not text or not isinstance(text, str):
        return text
    
    # Remove emojis first
    text = remove_emojis(text)
    
    # Replace newlines and carriage returns with spaces
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Trim
    text = text.strip()
    
    return text

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

@dataclass
class Business:
    """holds business data"""
    name: Optional[str] = None
    address: Optional[str] = None
    domain: Optional[str] = None
    website: Optional[str] = None
    phone_number: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    reviews_count: Optional[int] = None
    reviews_average: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_maps_link: Optional[str] = None
    scraped_query: Optional[str] = None
    scraped_at: Optional[str] = None
    
    def __hash__(self):
        """Make Business hashable for duplicate detection.
        Consider businesses different if:
        - Name is different, OR
        - Same name but different non-empty contact info (domain/website/phone)
        """
        # Create a tuple of fields that must match for duplicates
        # We'll include name plus any non-empty contact info fields
        hash_fields = [self.name]
        # Only include contact info fields if they're not empty
        if self.domain:
            hash_fields.append(f"domain:{self.domain}")
        if self.website:
            hash_fields.append(f"website:{self.website}")
        if self.phone_number:
            hash_fields.append(f"phone:{self.phone_number}")
        
        return hash(tuple(hash_fields))

import sys
import time
from typing import Optional

if sys.platform != 'win32':
    import fcntl
else:
    import msvcrt

class FileLock:
    """Simple cross-platform file locking."""
    def __init__(self, filename: str, timeout: int = 10):
        self.filename = filename 
        self.timeout = timeout
        self.handle: Optional[any] = None
        self.lock_file = f"{filename}.lock"

    def __enter__(self):
        # Create lock file if not exists
        if not os.path.exists(os.path.dirname(self.lock_file)):
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
              
        self.handle = open(self.lock_file, 'w')
        start_time = time.time()
        while True:
            try:
                if self.handle and sys.platform == 'win32':
                    # Lock first byte
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                elif self.handle:
                    fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (IOError, OSError):
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock for {self.filename} after {self.timeout}s")
                time.sleep(0.1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.handle and sys.platform == 'win32':
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            elif self.handle:
                fcntl.flock(self.handle, fcntl.LOCK_UN)
        except:
            pass
        if self.handle:
            self.handle.close()

@dataclass
class BusinessList:
    """holds list of Business objects,
    and save to both excel and csv
    """
    business_list: list[Business] = field(default_factory=list)
    _seen_businesses: set = field(default_factory=set, init=False)
    save_at = 'GMaps Data'

    def add_business(self, business: Business):
        """Add a business to the list if it's not a duplicate based on key attributes"""
        business_hash = hash(business)
        if business_hash not in self._seen_businesses:
            self.business_list.append(business)
            self._seen_businesses.add(business_hash)
    
    def dataframe(self):
        """transform business_list to pandas dataframe

        Returns: pandas dataframe
        """
        df = pd.json_normalize(
            [asdict(business) for business in self.business_list], sep="_"
        )
        
        # Apply text cleaning to all string columns as final safety layer
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns
                df[col] = df[col].apply(lambda x: clean_text_for_csv(x) if isinstance(x, str) else x)
        
        return df


    def save_to_csv(self, filename) -> str:
        """saves pandas dataframe to csv file. Returns path.
        Appends to existing file if present. Safe with File Locking.
        """
        os.makedirs(self.save_at, exist_ok=True)
        # Use filename parameter if provided, otherwise default to 'Gmaps Leads'
        target_file = filename if filename else "Gmaps Leads"
        path = f"{self.save_at}/{target_file}.csv"
            if os.path.exists(path) and os.path.getsize(path) == 0:
                header = True
                
            # Use utf-8-sig encoding for Excel compatibility (adds BOM)
            df.to_csv(path, index=False, mode='a', header=header, encoding='utf-8-sig')
            
        return path

    def save_to_db(self) -> int:
        """
        Saves the business list to the SQLite database.
        Returns the number of new records inserted.
        """
        try:
            from src import db
            count = 0
            for business in self.business_list:
                # Convert dataclass to dict
                data = asdict(business)
                # Generate key (re-use logic or trust db to handle it? DB handle it via unique_key param)
                # We need to pass the key explicitly to db.insert_business
                key = generate_unique_key(data)
                
                if db.insert_business(data, key):
                    count += 1
            return count
        except ImportError:
            print("   ⚠️  Database module not found. Skipping DB save.")
            return 0
        except Exception as e:
            print(f"   ⚠️  DB Save Error: {e}")
            return 0

def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """helper function to extract coordinates from url"""
    try:
        coordinates = url.split('/@')[-1].split('/')[0]
        return float(coordinates.split(',')[0]), float(coordinates.split(',')[1])
    except:
        return 0.0, 0.0

def print_sheet_status(action, sheet_name="N/A", sheet_id="N/A", details=""):
    """Helper to print beautiful, standardized sheet logs."""
    # ANSI escape codes for colors (if terminal supports them, else just text)
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Clean up ID if it's an object
    if sheet_id and hasattr(sheet_id, 'id'): sheet_id = sheet_id.id
    
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    
    print(f"{CYAN}   [SHEETS] {BOLD}{action:<10}{RESET} | 📄 {sheet_name}")
    print(f"{CYAN}            🔗 {sheet_url}{RESET}")
    if details:
        print(f"{YELLOW}            ↳ {details}{RESET}")

def connect_to_sheets(credentials_file=CREDENTIALS_FILE):
    """Connects to Google Sheets using credentials.json"""
    if not os.path.exists(credentials_file):
        print(f"Error: {credentials_file} not found. Please place your Google Service Account credentials in the project root.")
        return None

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error connecting to sheets: {e}")
        return None

def get_or_create_worksheet(client, sheet_name=SHEET_NAME, worksheet_title="Data 1", behavior="Append"):
    """
    Gets a worksheet by title, or creates it if it doesn't exist.
    Behavior:
    - 'Append': Open existing or create if missing.
    - 'Overwrite': Open existing, CLEAR content, add headers.
    - 'New Sheet': Ignore worksheet_title, find next available 'Data X' and create it.
    """
    try:
        spreadsheet = client.open(sheet_name)
        
        if behavior == "New Sheet":
            # Find next available Data X
            existing_titles = [ws.title for ws in spreadsheet.worksheets()]
            i = 1
            while f"Data {i}" in existing_titles:
                i += 1
            final_title = f"Data {i}"
            ws = spreadsheet.add_worksheet(title=final_title, rows=1000, cols=20)
            ws.append_row(EXPECTED_HEADERS)
            print_sheet_status("CREATE", spreadsheet.title, spreadsheet.id, f"Created NEW sheet '{final_title}' (New Sheet Mode)")
            return ws

        # For Append or Overwrite, we try to get the specific title
        try:
            worksheet = spreadsheet.worksheet(worksheet_title)
            print_sheet_status("ACCESS", spreadsheet.title, spreadsheet.id, f"Opened worksheet '{worksheet_title}'")
            
            if behavior == "Overwrite":
                print_sheet_status("CLEAR", spreadsheet.title, spreadsheet.id, f"Overwriting '{worksheet_title}'...")
                worksheet.clear()
                worksheet.append_row(EXPECTED_HEADERS)
                
            return worksheet
            
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=worksheet_title, rows=1000, cols=20)
            # Add headers for new sheet
            ws.append_row(EXPECTED_HEADERS) 
            print_sheet_status("CREATE", spreadsheet.title, spreadsheet.id, f"Created new worksheet '{worksheet_title}'")
            return ws
            
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
            
    # 3. Dynamic Column Addition
    # Check if df has columns that are NOT in existing_headers
    df_cols = list(df.columns)
    new_cols_to_add = [c for c in df_cols if c not in existing_headers]
    
    if new_cols_to_add:
        print(f"   🛠️  Sheet Schema Update: Found {len(new_cols_to_add)} new columns: {new_cols_to_add}")
        # Add them to the sheet header row
        # We need to find the column index to start appending
        next_col_idx = len(existing_headers) + 1
        
        # We can use update logic or append at specific cells
        # Construct the range for new headers
        # E.g. existing 10 cols, adding 2. Range starts at col 11 (K1)
        # However, gspread uses A1 notation or row/col.
        
        # Simplest: Update cells in row 1
        # Update existing_headers in memory + on sheet
        # We assume headers are in row 1
        
        try:
            # row=1, col=next_col_idx is where we start
            # values needs to be a list of lists [[col1, col2]] for update? or just list for update_cell?
            # update accepts range or list of lists.
            # Convert col index to letters? No, row/col integers works for cell(), usually need range for update.
            # Let's use individual updates for safety or batch update if possible.
            # Or assume we can just get the range.
            # Using gspread 'update' with list of lists is standard.
            
            # Convert column index to A1 notation would be complex without helper.
            # But worksheet.update_cell(row, col, value) is easy but slow loop.
            # worksheet.update(range_name, values)
            
            # We'll use the loop for simplicity if small number, or carefully construct range.
            # Actually, `worksheet.resize(cols=total_cols)` might be needed if restricted?
            # Usually strict limit isn't default but let's be safe.
            
            current_col_count = worksheet.col_count
            needed_col_count = len(existing_headers) + len(new_cols_to_add)
            if needed_col_count > current_col_count:
                worksheet.resize(cols=needed_col_count + 5)
            
            # Batch update headers
            # Range starting from (1, next_col_idx)
            # We can use gspread's row/col update if available?
            # worksheet.update(values=[new_cols_to_add], range_name=...?)
            # Since gspread v6, methods changed. Let's use safe `update_cell` loop as fallback or find range.
            # Actually, standard update takes `range_name` (e.g. 'D1:E1').
            # Calculating A1 notation is annoying.
            # Let's use `update_cell` for robustness right now as we are likely adding 1-2 cols max.
            
            col_offset = 0
            for new_col in new_cols_to_add:
                worksheet.update_cell(1, next_col_idx + col_offset, new_col)
                col_offset += 1
                
            existing_headers.extend(new_cols_to_add)
            print("   ✅ Updated Sheet Headers.")
            
        except Exception as e:
            print(f"   ⚠️  Failed to add columns to sheet: {e}")

    # 4. Reorder DF to match Final Sheet Headers (Existing + New)
    # Any columns in DF that are not in existing_headers (should be none now) will be lost?
    # No, we just added them.
    # What if existing_headers has columns NOT in DF? We need to keep them (ignoring empty vals for them)
    # We should return a DF that has ALL columns in existing_headers order.
    
    for h in existing_headers:
        if h not in df.columns:
            df[h] = ""
            
    final_df = df[existing_headers].copy()
    
    return final_df

def upload_data_to_sheet(worksheet, df_new):
    """
    Handles the deduplication and upload of data provided in df_new.
    Returns logic summary (added, duplicate).
    """
    
    # 1. Fetch Existing Keys
    print_sheet_status("CHECKING", worksheet.spreadsheet.title, worksheet.spreadsheet.id, "Reading existing data for deduplication...")
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
        print_sheet_status("SKIPPED", worksheet.spreadsheet.title, worksheet.spreadsheet.id, "All records already exist.")
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
        
        print_sheet_status("WRITING", worksheet.spreadsheet.title, worksheet.spreadsheet.id, f"Appending {len(new_rows)} rows starting at {range_name}")
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
            print_sheet_status("READING", worksheet.spreadsheet.title, worksheet.spreadsheet.id, "Fetching known URLs for optimization...")
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

def get_all_known_names(worksheet=None, local_dir='GMaps Data'):
    """
    Returns a set of all known Business Names (normalized to lowercase) 
    from both online sheet and local DB (SQLite).
    """
    known_names = set()
    
    # 1. From Sheets
    if worksheet:
        try:
            print_sheet_status("READING", worksheet.spreadsheet.title, worksheet.spreadsheet.id, "Fetching known Names for pre-filtering...")
            headers = worksheet.row_values(1)
            name_col_idx = -1
            
            candidates = ['Name', 'name', 'Business Name']
            for i, h in enumerate(headers):
                if h in candidates:
                    name_col_idx = i + 1
                    break
            
            if name_col_idx != -1:
                names = worksheet.col_values(name_col_idx)
                if names and names[0] in candidates:
                    names = names[1:] # Skip header
                
                for n in names:
                    if n and isinstance(n, str) and n.strip():
                        known_names.add(n.strip().lower())
        except Exception as e:
            print(f"Error reading names from sheet: {e}")

    # 2. From Local DB (SQLite) - Preferred
    try:
        from src import db
        # We assume db module exists and is initialized
        # If DB file doesn't exist, this might return empty, which is fine
        db_names = db.get_known_names()
        known_names.update(db_names)
        return known_names
    except Exception:
        # Fallback to CSV scanning if DB fails or not present (legacy support)
        pass

    return known_names

def prune_duplicates(worksheet):
    """
    Reads all data from the sheet, identifies duplicates using generate_unique_key,
    and rewrites the sheet with only unique records.
    """
    try:
        print_sheet_status("CLEANING", worksheet.spreadsheet.title, worksheet.spreadsheet.id, "Scanning for duplicates to prune...")
        
        # 1. Read All Data
        all_values = worksheet.get_all_values()
        if not all_values or len(all_values) < 2:
            print("            ↳ Sheet is empty or just headers. Skipping.")
            return

        headers = all_values[0]
        data_rows = all_values[1:]
        
        # 2. Identify Unique Rows
        unique_rows = []
        seen_keys = set()
        duplicates_count = 0
        
        # Map headers to indices for key generation
        def get_col_index(name_variations):
            for name in name_variations:
                if name in headers: return headers.index(name)
            return -1

        name_idx = get_col_index(['Name', 'name'])
        phone_idx = get_col_index(['Phone Number', 'phone_number', 'Phone'])
        address_idx = get_col_index(['Address', 'address'])

        for row in data_rows:
            # Build minimal dict for key generation
            row_data = {}
            if name_idx != -1 and name_idx < len(row): row_data['Name'] = row[name_idx]
            if phone_idx != -1 and phone_idx < len(row): row_data['Phone Number'] = row[phone_idx]
            if address_idx != -1 and address_idx < len(row): row_data['Address'] = row[address_idx]
            
            key = generate_unique_key(row_data)
            
            if key and key in seen_keys:
                duplicates_count += 1
            else:
                if key: seen_keys.add(key)
                unique_rows.append(row)
        
        if duplicates_count == 0:
            print("            ↳ No duplicates found. Sheet is clean.")
            return

        # 3. Rewrite Sheet (Safe Mode: Clear and Upload)
        print(f"            ↳ Found {duplicates_count} duplicates. Removing...")
        
        # We rewrite everything: Headers + Unique Data
        new_data = [headers] + unique_rows
        
        # Clear sheet content
        worksheet.clear()
        
        # Batch Update
        worksheet.update(values=new_data)
        
        print(f"            ↳ ✅ Pruned {duplicates_count} duplicates. Total rows: {len(new_data)}")
        
    except Exception as e:
        print(f"            ❌ Error pruning duplicates: {e}")
