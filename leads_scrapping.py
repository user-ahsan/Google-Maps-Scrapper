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
        return sheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return sheet.add_worksheet(title=title, rows=1000, cols=20)

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
    while True:
        page.mouse.wheel(0, 10000)
        page.wait_for_timeout(3000)

        current_count = page.locator(
            '//a[contains(@href, "https://www.google.com/maps/place")]'
        ).count()

        if current_count >= total:
            listings = page.locator(
                '//a[contains(@href, "https://www.google.com/maps/place")]'
            ).all()[:total]
            listings = [listing.locator("xpath=..") for listing in listings]
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

    # Detailed scraping
    for i, listing in enumerate(listings):
        try:                        
            listing.click()
            page.wait_for_timeout(2000)
            
            # Detailed Logging
            print(f"[{i+1}/{len(listings)}] Clicking listing...", end='\r')

            name_attribute = 'h1.DUwDvf' 
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            review_count_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//span'
            reviews_average_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]' 
                                                   
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
                
            # Reviews Count
            try:
                if page.locator(review_count_xpath).count() > 0:
                    count_text = page.locator(review_count_xpath).first.inner_text(timeout=3000)
                    business.reviews_count = int(count_text.split()[0].replace(',', '').strip())
                else:
                    business.reviews_count = None
            except:
                 business.reviews_count = None
                
            # Reviews Average
            try:
                if page.locator(reviews_average_xpath).count() > 0:
                    avg_text = page.locator(reviews_average_xpath).first.get_attribute('aria-label', timeout=3000)
                    business.reviews_average = float(avg_text.split()[0].replace(',', '.').strip())
                else:
                    business.reviews_average = None
            except:
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
    print("--- Google Sheets Leads Scraper (Input: input.txt, Output: Sheets) ---")
    
    # 1. Read input.txt
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r') as f:
        queries = [line.strip() for line in f.readlines() if line.strip()]

    if not queries:
        print(f"No queries found in {INPUT_FILE}")
        return

    print(f"Found {len(queries)} queries in {INPUT_FILE}")

    # 2. Connect to Sheets
    try:
        client = connect_to_sheets()
        spreadsheet = client.open(SHEET_NAME)
        
        # PRINT THE URL so the user knows exactly where data is going
        print(f"✅ Connected to Sheet: '{spreadsheet.title}'")
        print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet.id}")

        # Explicitly get or create a 'Leads' worksheet to avoid 'Sheet1' ambiguity
        try:
            worksheet = spreadsheet.worksheet("Leads")
        except gspread.WorksheetNotFound:
            print("Creating new worksheet named 'Leads'...")
            worksheet = spreadsheet.add_worksheet(title="Leads", rows=1000, cols=20)

        print(f"📝 Writing to Worksheet: '{worksheet.title}'")
        
        # Check/Add headers if empty
        if not worksheet.get_all_values():
            headers = [
                "Name", "Address", "Domain", "Website", "Phone Number", 
                "Category", "Location", "Reviews Count", "Reviews Average", 
                "Latitude", "Longitude", "Google Maps Link", "Scraped Query", "Scraped At"
            ]
            worksheet.append_row(headers)
            print("Added headers to the sheet.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Failed to connect to sheet: {e}")
        return

    # 3. Start Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="en-GB")
        
        page.goto("https://www.google.com/maps", timeout=20000)
        page.wait_for_timeout(2000)

        for i, query in enumerate(queries):
            print(f"\nProcessing Query {i+1}/{len(queries)}: {query}")
            
            try:
                # Scrape
                b_list = scrape_data(page, query, TOTAL_RESULTS_PER_QUERY)
                
                # Prepare dataframe
                df = b_list.dataframe()
                if df.empty:
                    print(f"No results scraped for '{query}'. Skipping upload.")
                    continue
                
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df['Scraped_Query'] = query
                df['Scraped_At'] = current_time

                # Convert to list of lists for gspread 
                # (Handle NaNs because JSON/gspread doesn't like them)
                df = df.fillna("")
                data_to_upload = df.values.tolist()
                
                # Append to Sheet
                worksheet.append_rows(data_to_upload)
                print(f"Uploaded {len(data_to_upload)} rows to Google Sheet.")
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Error processing query '{query}': {e}")
            
            time.sleep(5) 

        browser.close()
    
    print("\nAll queries processed.")

if __name__ == "__main__":
    main()
