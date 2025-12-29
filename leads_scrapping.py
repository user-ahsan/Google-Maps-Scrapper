import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
import sys
import datetime
import time
from playwright.sync_api import sync_playwright

# Import existing classes and helpers from main.py
try:
    from main import Business, BusinessList, extract_coordinates_from_url
except ImportError:
    print("Error: Could not import from main.py. Make sure it is in the same directory.")
    sys.exit(1)

# --- Configuration ---
SHEET_NAME = "Gmaps Leads"  # The Google Sheet to save results to
CREDENTIALS_FILE = "credentials.json"
TOTAL_RESULTS_PER_QUERY = 100 # Adjust as needed or make dynamic
INPUT_FILE = "input.txt"

def connect_to_sheets():
    """Connects to Google Sheets using credentials.json"""
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Error: {CREDENTIALS_FILE} not found. Please place your Google Service Account credentials in the project root.")
        sys.exit(1)

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client

def get_or_create_worksheet(sheet, title="Sheet1"):
    """Gets a worksheet by title, or creates it if it doesn't exist."""
    try:
        worksheet = sheet.worksheet(title)
        return worksheet
    except gspread.WorksheetNotFound:
        return sheet.add_worksheet(title=title, rows=1000, cols=20)

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
        
        print(f"   -> Found {len(existing_keys)} existing unique records in the sheet.")
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
        "Scraped_Query": "Scraped Query",
        "Scraped_At": "Scraped At"
    }

    # Possible aliases for each field (Dictionary of specified header -> internal key)
    # We invert the logic: Look at sheet header -> decide which internal field maps to it
    HEADER_ALIASES = {
        'name': 'name', 'business name': 'name', 'title': 'name',
        'address': 'address', 'full address': 'address',
        'domain': 'domain', 'website': 'website', 'site': 'website', 'url': 'website',
        'phone': 'phone_number', 'phone number': 'phone_number', 'tel': 'phone_number', 'mobile': 'phone_number',
        'category': 'category', 'type': 'category',
        'location': 'location', 'city': 'location',
        'reviews': 'reviews_count', 'reviews count': 'reviews_count', 'count': 'reviews_count',
        'rating': 'reviews_average', 'score': 'reviews_average', 'reviews average': 'reviews_average', 'average': 'reviews_average', 'stars': 'reviews_average',
        'latitude': 'latitude', 'lat': 'latitude',
        'longitude': 'longitude', 'long': 'longitude', 'lng': 'longitude',
        'link': 'google_maps_link', 'google maps link': 'google_maps_link', 'maps link': 'google_maps_link', 'url': 'google_maps_link',
        'query': 'Scraped_Query', 'search query': 'Scraped_Query', 'scraped query': 'Scraped_Query',
        'time': 'Scraped_At', 'scraped at': 'Scraped_At', 'date': 'Scraped_At'
    }

    try:
        # Get existing headers from the sheet
        existing_headers = worksheet.row_values(1)
    except:
        existing_headers = []

    if not existing_headers:
        # Sheet is empty, use default headers
        print("   -> Sheet is empty. Setting up default headers...")
        default_headers = list(DEFAULT_MAPPING.values())
        worksheet.append_row(default_headers)
        existing_headers = default_headers

    # Build the specific rename map for THIS sheet
    # We iterate through existing headers and see if we can claim them for our data
    dynamic_rename_map = {}
    used_internal_cols = set()

    for header in existing_headers:
        header_lower = str(header).strip().lower()
        if header_lower in HEADER_ALIASES:
            internal_field = HEADER_ALIASES[header_lower]
            if internal_field not in used_internal_cols:
                # Found a match! Map internal_field -> This Header
                dynamic_rename_map[internal_field] = header
                used_internal_cols.add(internal_field)
    
    # For any internal field NOT found in the sheet, we rename it to its Default Display Name
    # (It will likely be dropped later if we strictly follow sheet headers, 
    # but strictly following sheet headers IS respecting existing data)
    for internal, default_display in DEFAULT_MAPPING.items():
        if internal not in dynamic_rename_map:
            dynamic_rename_map[internal] = default_display

    # Apply renaming
    df = df.rename(columns=dynamic_rename_map)

    # Reorder DF to match Sheet order EXACTLY
    # Identify missing columns in DF and fill with empty string
    for header in existing_headers:
        if header not in df.columns:
            df[header] = ""

    final_columns = []
    for header in existing_headers:
        # Only keep columns that are in the dataframe (which now includes empty fills for missing headers)
        if header in df.columns:
            final_columns.append(header)
        else:
             # Should be covered by loop above, but safety fallback
             df[header] = ""
             final_columns.append(header)

    final_df = df[final_columns].copy()
    
    return final_df

def scrape_data(page, search_for, total):
    """
    Scrapes data for a single query using the provided Playwright page.
    """
    print(f"To Scrape: {search_for}")

    page.locator('//input[@id="searchboxinput"]').fill(search_for)
    page.wait_for_timeout(3000)

    page.keyboard.press("Enter")
    page.wait_for_timeout(5000)

    # Check if results found
    try:
        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=5000)
    except:
        print("No results found or page layout changed.")
        return BusinessList()

    previously_counted = 0
    retry_count = 0
    MAX_RETRIES = 5

    # Scroll and load loop
    # Optimization: Target the specific feed div for scrolling
    feed_selector = 'div[role="feed"]'
    
    while True:
        # Check if feed exists, if not, try hovering generic list
        if page.locator(feed_selector).count() > 0:
            # Scroll the feed directly
            page.locator(feed_selector).evaluate("node => node.scrollTop += 5000")
        else:
            # Scroll and load loop
            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(3000)

        current_count = page.locator(
            '//a[contains(@href, "https://www.google.com/maps/place")]'
        ).count()

        if current_count >= total:
            listings = page.locator(
                '//a[contains(@href, "https://www.google.com/maps/place")]'
            ).all()[:total]
            print(f"Total Found: {len(listings)}")
            break
        
        if current_count == previously_counted:
            retry_count += 1
            print(f"Retry {retry_count}/{MAX_RETRIES} - Waiting for more results...", end='\r')
            if retry_count >= MAX_RETRIES:
                listings = page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).all()
                print(f"\nArrived at all available or stalled.\nTotal Found: {len(listings)}")
                break
            page.wait_for_timeout(2000)
        else:
            previously_counted = current_count
            retry_count = 0
            print(
                f"Currently Loaded: {current_count}", end='\r'
            )

    business_list = BusinessList()
    visited_urls = set() # Optimization: Track unique URLs to avoid clicking duplicates

    # Detailed scraping
    processed_count = 0
    for i, listing in enumerate(listings):
        try:
            # Optimization: Get URL first to check for duplicates
            href = listing.get_attribute('href')
            if not href:
                 continue
                 
            # Extract basic ID from URL to dedupe (simplified)
            if href in visited_urls:
                continue
            visited_urls.add(href)
            
            processed_count += 1
            print(f"[{processed_count}/{len(listings)}] Clicking listing...", end='\r')
            
            listing.click()
            page.wait_for_timeout(2000)
            
            # Name and Anchor H1
            name_attribute = 'h1.DUwDvf' 
            try:
                 page.wait_for_selector(name_attribute, timeout=3000)
            except Exception:
                 print(f"   -> Warning: H1 element (business name) not found after clicking listing {processed_count}. Skipping detailed scrape for this item.")
                 continue # Skip to next listing if H1 is not found

            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                                                   
            business = Business()

            def get_text_safe(locator_xpath, timeout=3000):
                try:
                    loc = page.locator(locator_xpath).first
                    return loc.inner_text(timeout=timeout).strip()
                except Exception:
                    return ""

            # Name
            try:
                if page.locator(name_attribute).count() > 0:
                    business.name = page.locator(name_attribute).first.inner_text(timeout=5000).strip()
                elif page.locator('h1').count() > 0:
                     all_h1s = page.locator('h1').all()
                     business.name = ""
                     for h1 in all_h1s:
                         try:
                             text = h1.inner_text(timeout=2000).strip()
                             if text and "Results" not in text:
                                 business.name = text
                                 break
                         except:
                             continue
                else:
                    business.name = ""
            except:
                business.name = ""

            # Address
            business.address = get_text_safe(address_xpath)

            # Website
            website_text = get_text_safe(website_xpath)
            if website_text:
                business.domain = website_text
                business.website = f"https://www.{website_text}"
            else:
                business.domain = ""
                business.website = ""

            # Phone
            business.phone_number = get_text_safe(phone_number_xpath)
                
            # Reviews Count & Average
            try:
                # Reliability Strategy: Use the Business Name H1 as an anchor.
                h1_xpath = '//h1[contains(@class, "DUwDvf")]'
                
                # XPath to find the first rating/review span occurring after the H1
                rating_xpath = f'{h1_xpath}/following::span[contains(@class, "MW4etd")][1]'
                review_count_xpath = f'{h1_xpath}/following::span[contains(@class, "UY7F9")][1]'

                # 1. Rating
                if page.locator(rating_xpath).count() > 0:
                    rating_text = page.locator(rating_xpath).first.inner_text(timeout=3000).replace(',', '.')
                    business.reviews_average = float(rating_text)
                else:
                    business.reviews_average = None

                # 2. Review Count
                if page.locator(review_count_xpath).count() > 0:
                    count_text = page.locator(review_count_xpath).first.inner_text(timeout=3000)
                    # Text is usually like "(1,234)" or "1,234"
                    clean_count = count_text.replace('(', '').replace(')', '').replace(',', '').strip()
                    if clean_count:
                         business.reviews_count = int(clean_count)
                    else:
                         business.reviews_count = None
                else:
                    business.reviews_count = None

                # 3. Fallback: Aria-Label on container relative to H1? 
                # Or just generic fallback if primary failed
                if business.reviews_average is None or business.reviews_count is None:
                    # Try finding the aria-label on the stars container which is usually the parent of rating span
                    # We can use the already found rating element to find its parent
                    if business.reviews_average:
                         # Use JS to get parent's aria-label
                         aria_label = page.locator(rating_xpath).first.locator('xpath=..').get_attribute('aria-label')
                         if aria_label and "Reviews" in aria_label:
                              # Parse count from "4.0 stars 982 Reviews"
                              import re
                              count_match = re.search(r'([\d,]+) Reviews', aria_label, re.IGNORECASE)
                              if count_match and business.reviews_count is None:
                                   business.reviews_count = int(count_match.group(1).replace(',', ''))
                    
                    # If total failure, try generic aria lookup (risky but better than 0)
                    if business.reviews_count is None:
                         aria_fallback_xpath = '//span[@role="img" and contains(@aria-label, "stars") and contains(@aria-label, "Reviews")]'
                         if page.locator(aria_fallback_xpath).count() > 0:
                              # Pick the first one visible? Or one inside main?
                              # Let's hope the detail pane one is first or prominent
                              aria_label = page.locator(aria_fallback_xpath).first.get_attribute('aria-label')
                              if aria_label:
                                   import re
                                   rating_match = re.search(r'(\d+(\.\d+)?) stars', aria_label)
                                   count_match = re.search(r'([\d,]+) Reviews', aria_label, re.IGNORECASE)
                                   
                                   if rating_match and business.reviews_average is None:
                                        business.reviews_average = float(rating_match.group(1))
                                   if count_match and business.reviews_count is None:
                                        business.reviews_count = int(count_match.group(1).replace(',', ''))

            except Exception as e:
                print(f"   -> Warning: Could not extract reviews: {e}")
                business.reviews_count = None
                business.reviews_average = None

            business.category = search_for.split(' in ')[0].strip()
            business.location = search_for.split(' in ')[-1].strip()
            business.latitude, business.longitude = extract_coordinates_from_url(page.url)
            business.google_maps_link = page.url

            business_list.add_business(business)
            
            # Print success summary for this item
            print(f"✅ Found: {business.name[:30]:<30} | ⭐ {business.reviews_average or 'N/A'} ({business.reviews_count or 0}) | 📞 {business.phone_number or 'No Phone'}")
            
        except Exception as e:
            print(f'❌ Error scraping item {i}: {e}')
    
    return business_list

def main():
    print("\n" + "="*60)
    print("   GOOGLE SHEETS LEADS SCRAPER - ENHANCED   ")
    print("="*60 + "\n")
    
    # 1. Read input.txt
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r') as f:
        queries = [line.strip() for line in f.readlines() if line.strip()]

    if not queries:
        print(f"No queries found in {INPUT_FILE}")
        return

    print(f"📄 Found {len(queries)} queries in {INPUT_FILE}")

    # 2. Connect to Sheets
    try:
        print("🔌 Connecting to Google Sheets...")
        client = connect_to_sheets()
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.sheet1 # Assuming first sheet
        
        # Enhanced Logging
        print("-" * 60)
        print(f"✅ CONNECTED SUCCESSFULLY")
        print(f"   Spreadsheet Title: {spreadsheet.title}")
        print(f"🔗 Sheet URL:       https://docs.google.com/spreadsheets/d/{spreadsheet.id}")
        print(f"   Worksheet Title:   {worksheet.title}")
        print("-" * 60)
        
        # Check/Add headers if empty (Robust Check)
        try:
            row1 = worksheet.row_values(1)
            if not row1:
                print("   -> Sheet is empty (no headers). Adding default headers...")
                headers = [
                    "Name", "Address", "Domain", "Website", "Phone Number", 
                    "Category", "Location", "Reviews Count", "Reviews Average", 
                    "Latitude", "Longitude", "Google Maps Link", "Scraped Query", "Scraped At"
                ]
                worksheet.insert_row(headers, index=1, value_input_option='USER_ENTERED')
                print("   -> Headers added to Row 1.")
            else:
                print("   -> Headers found in Row 1.")
        except Exception as header_err:
             print(f"   -> Warning checking headers: {header_err}")

        # Determine existing data size
        try:
            print(f"   Total Rows in Sheet: {worksheet.row_count}")
        except:
            pass
        print("-" * 60)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Failed to connect to sheet: {e}")
        return

    # 3. Start Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="en-GB")
        
        page.goto("https://www.google.com/maps", timeout=20000)
        page.wait_for_timeout(2000)

        for i, query in enumerate(queries):
            print(f"\n🔎 Processing Query {i+1}/{len(queries)}: {query}")
            
            try:
                # Scrape
                b_list = scrape_data(page, query, TOTAL_RESULTS_PER_QUERY)
                
                # Prepare dataframe from scraped data
                df_new = b_list.dataframe()
                if df_new.empty:
                    print(f"⚠️ No results scraped for '{query}'. Skipping upload.")
                    continue
                    
                # Add metadata columns
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df_new['Scraped_Query'] = query
                df_new['Scraped_At'] = current_time

                # --- DEDUPLICATION LOGIC ---
                # Fetch existing keys FRESH for every query loop to handle real-time updates
                print("   Checking for duplicates...")
                existing_keys = get_existing_keys(worksheet)
                
                # Check mapping first to get 'Name', 'Phone Number' columns aligned for key generation
                # We need to use internal names for 'generate_unique_key' to work on raw DF, 
                # OR we map first then use display names.
                # Let's simple MAP FIRST -> standardize everything to Sheet format.
                df_mapped = map_columns_to_sheet(df_new, worksheet)
                
                # Filter duplicates
                initial_count = len(df_mapped)
                
                # Determine new rows
                # We need to construct the key using the SHEET COLUMN NAMES now
                new_rows = []
                for index, row in df_mapped.iterrows():
                    key = generate_unique_key(row)
                    if key not in existing_keys:
                        new_rows.append(row)
                        existing_keys.add(key) # Add to local set to prevent dupes within same batch
                
                if not new_rows:
                    print(f"⚠️ All {initial_count} scraped items were duplicates. Nothing to add.")
                    continue
                
                print(f"✅ New unique records to add: {len(new_rows)} (Excluded {initial_count - len(new_rows)} duplicates)")
                
                # Convert back to DF for saving (or just list of lists)
                df_final = pd.DataFrame(new_rows)
                
                # Handle NaNs
                df_final = df_final.fillna("")

                # ESCAPE PHONE NUMBERS (Fix for Formula Parse Error)
                # Google Sheets treats values starting with '=' or '+' as formulas.
                # We prepend a single quote to force text formatting for phone entries.
                for col in df_final.columns:
                    if any(x in str(col).lower() for x in ['phone', 'mobile', 'tel']):
                         df_final[col] = df_final[col].apply(lambda x: f"'{x}" if str(x).strip().startswith('+') else x)

                data_to_upload = df_final.values.tolist()
                
                # Explicitly calculate the next empty row based on Column A
                # This ensures we always start writing at Column A, next available row
                # Avoiding gspread's append_rows which might detect "table ends" incorrectly
                try:
                    # Get all values in column A to see how many rows are filled
                    col_a_values = worksheet.col_values(1)
                    next_row = len(col_a_values) + 1
                    
                    # Define the range to update: A{next_row}
                    # We accept that columns might expand beyond current headers if new data has more columns (but we mapped it so it shouldn't)
                    range_name = f"A{next_row}"
                    
                    print(f"   Writing data starting at cell {range_name}...")
                    worksheet.update(range_name=range_name, values=data_to_upload, value_input_option='USER_ENTERED')
                    print(f"🚀 Uploaded {len(data_to_upload)} rows to Google Sheet.")
                except Exception as ex:
                    print(f"   -> Error writing to sheet: {ex}")
                    # Fallback
                    worksheet.append_rows(data_to_upload, value_input_option='USER_ENTERED')
                    print(f"   -> (Used fallback append_rows)")
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"❌ Error processing query '{query}': {e}")
            
            time.sleep(5) 

        browser.close()
    
    print("\n" + "="*60)
    print("🎉 ALL QUERIES PROCESSED SUCCESSFULLY")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
