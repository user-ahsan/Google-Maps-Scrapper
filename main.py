import datetime
from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
import os
import sys
import glob

# Try to import sheets_utils
try:
    import sheets_utils
except ImportError:
    sheets_utils = None

@dataclass
class Business:
    """holds business data"""
    name: str = None
    address: str = None
    domain: str = None
    website: str = None
    phone_number: str = None
    category: str = None
    location: str = None
    reviews_count: int = None
    reviews_average: float = None
    latitude: float = None
    longitude: float = None
    latitude: float = None
    longitude: float = None
    google_maps_link: str = None
    scraped_query: str = None
    scraped_at: str = None
    
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

@dataclass
class BusinessList:
    """holds list of Business objects,
    and save to both excel and csv
    """
    business_list: list[Business] = field(default_factory=list)
    _seen_businesses: set = field(default_factory=set, init=False)
    business_list: list[Business] = field(default_factory=list)
    _seen_businesses: set = field(default_factory=set, init=False)
    # today = datetime.datetime.now().strftime("%Y-%m-%d") <-- REMOVED DATE DIR
    save_at = 'GMaps Data'
    # os.makedirs(save_at, exist_ok=True)  <-- REMOVED: Prevent auto-creation

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
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file

        Args:
            filename (str): filename
        """
        os.makedirs(self.save_at, exist_ok=True)
        self.dataframe().to_excel(f"{self.save_at}/{filename}.xlsx", index=False)

    def save_to_csv(self, filename) -> str:
        """saves pandas dataframe to csv file. Returns path.
        Appends to existing file if present.
        """
        os.makedirs(self.save_at, exist_ok=True)
        # FORCE filename to 'Gmaps Leads' regardless of input to enforce single file
        # We assume the caller sends a descriptive name, but we want one BIG file.
        # User requirement: "single csv file in the directory named the same as google sheet file which is Gmaps Data"
        # I suspect they want "GMaps Data/Gmaps Leads.csv"
        
        target_file = "Gmaps Leads"
        path = f"{self.save_at}/{target_file}.csv"
        
        df = self.dataframe()
        
        # Enforce Schema here too for local consistency
        if sheets_utils:
            expected = sheets_utils.EXPECTED_HEADERS
            # Rename columns to match expected headers using default mapping logic
            # This is duplicate logic but safe
            rename_map = {
                "name": "Name", "address": "Address", "domain": "Domain", "website": "Website",
                "phone_number": "Phone Number", "category": "Category", "location": "Location",
                "reviews_count": "Reviews Count", "reviews_average": "Reviews Average",
                "latitude": "Latitude", "longitude": "Longitude", "google_maps_link": "Google Maps Link",
                "scraped_query": "Scraped Query", "scraped_at": "Scraped At"
            }
            df = df.rename(columns=rename_map)
            
            # Ensure columns exist
            for h in expected:
                if h not in df.columns: df[h] = ""
            
            # Filter
            df = df[expected]
        
        header = not os.path.exists(path)
        df.to_csv(path, index=False, mode='a', header=header)
        return path

def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """helper function to extract coordinates from url"""
    try:
        coordinates = url.split('/@')[-1].split('/')[0]
        return float(coordinates.split(',')[0]), float(coordinates.split(',')[1])
    except:
        return 0.0, 0.0

# --- DIAGNOSTICS & SYNC ---

def run_diagnostics():
    """Run startup checks for Browser and Sheets."""
    print("\n" + "="*50)
    print("   🔍 STARTUP DIAGNOSTICS")
    print("="*50)

    # 1. Browser Connectivity Test
    print("1. Testing Browser Environment (Headless)...", end=" ")
    browser_ready = False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.google.com", timeout=10000)
            browser.close()
        print("✅ PASS")
        browser_ready = True
    except Exception as e:
        print(f"❌ FAIL\n   Error: {e}")
        print("   -> Tip: Ensure Playwright is installed: 'playwright install chromium'")

    # 2. Google Sheets Connectivity Test
    print("2. Testing Google Sheets Connection...", end=" ")
    sheets_client = None
    online_mode = False
    
    if sheets_utils:
        sheets_client = sheets_utils.connect_to_sheets()
        if sheets_client:
            print("✅ PASS")
            online_mode = True
        else:
            print("⚠️ CHECK FAILED")
            print("   -> Could not connect to Google Sheets. Will run in OFFLINE mode.")
    else:
        print("❌ FAIL (sheets_utils missing)")

    print("-" * 50)
    return browser_ready, sheets_client, online_mode

def sync_offline_data(sheets_client):
    """Check for existing CSVs and upload them if possible."""
    print("\n☁️ Checking for offline data to sync...")
    
    base_dir = 'GMaps Data'
    if not os.path.exists(base_dir):
        print("   No data directory found. Nothing to sync.")
        return

    # User wants ROBUST SINGLE FILE handling.
    # We should look for 'Gmaps Leads.csv' primarily.
    target_csv = os.path.join(base_dir, 'Gmaps Leads.csv')
    csv_files = []
    
    if os.path.exists(target_csv):
        csv_files.append(target_csv)
    
    # Also check legacy files just in case? 
    # User said: "should jsut ahave a single csv file"
    # But for "syncing offline data", we should likely ingest old files if they exist to be helpful?
    # No, strict instructions: "Robust data enrichment... syncing happens... robust file handling"
    # Let's stick to the MAIN file for now to avoid complexity with old schemas.
    
    if not csv_files:
        print("   No 'Gmaps Leads.csv' found.")
        return

    print(f"   Found {len(csv_files)} CSV file(s). Syncing...")
    
    worksheet = sheets_utils.get_or_create_worksheet(sheets_client)
    if not worksheet:
        print("   Could not access worksheet for sync.")
        return

    synced_count = 0
    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                continue
            
            # If large file, this might be heavy. 'upload_data_to_sheet' handles dupes.
            print(f"   Syncing {os.path.basename(csv_path)}...", end=" ")
            added, dupe = sheets_utils.upload_data_to_sheet(worksheet, df)
            print(f"Done. (+{added}, {dupe} dupes)")
            synced_count += 1
            
        except Exception as e:
            print(f"   Error syncing {csv_path}: {e}")

    if synced_count > 0:
        print(f"✅ Synced {synced_count} files to Google Sheets.")
    else:
        print("   Sync complete.")


def main():
    # read search from arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    parser.add_argument("-headed", "--headed", action="store_true", help="Run with browser visible")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-accept prompts")
    args = parser.parse_args()

    # 1. Run Diagnostics
    browser_ok, sheets_client, online_mode = run_diagnostics()

    # --- OPTIMIZATION: Pre-load SEEN URLS ---
    global_seen_urls = set()
    if sheets_utils:
        worksheet = None
        if online_mode and sheets_client:
            worksheet = sheets_utils.get_or_create_worksheet(sheets_client)
        
        # Load from both Online (if avail) and Offline
        global_seen_urls = sheets_utils.get_all_seen_urls(worksheet)
    # ----------------------------------------

    if not browser_ok:
        if not args.yes:
             input("\n❌ Browser test failed. Check errors above. Press Enter to try anyway (or Ctrl+C to quit)...")
    
    if online_mode:
        # 2. Sync Offline Data
        sync_offline_data(sheets_client)
    else:
        print("\n⚠️ ORANGE ALERT: Running in OFFLINE MODE. Data will be saved to CSV only.")
        if not args.yes:
             resp = input("   Continue? (Y/n): ")
             if resp.lower() == 'n':
                 sys.exit()
    
    if args.search:
        search_list = [args.search]
        
    if args.total:
        total = args.total
    else:
        # if no total is passed, we set the value to random big number
        total = 1_000_000

    if not args.search:
        search_list = []
        # read search from input.txt file
        input_file_name = 'input.txt'
        # Get the absolute path of the file in the current working directory
        input_file_path = os.path.join(os.getcwd(), input_file_name)
        # Check if the file exists
        if os.path.exists(input_file_path):
        # Open the file in read mode
            with open(input_file_path, 'r') as file:
            # Read all lines into a list
                search_list = [line.strip() for line in file.readlines() if line.strip()]
                
        if len(search_list) == 0:
            print('Error occured: You must either pass the -s search argument, or add searches to input.txt')
            sys.exit()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        page = browser.new_page(locale="en-GB")

        page.goto("https://www.google.com/maps", timeout=20000)
        
        for search_for_index, search_for in enumerate(search_list):
            print(f"-----\n{search_for_index} - {search_for}")

            page.locator('//input[@id="searchboxinput"]').fill(search_for)
            page.wait_for_timeout(3000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)

            # scrolling
            page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

            previously_counted = 0
            retry_count = 0
            MAX_RETRIES = 5

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
                    print(f"Total Scraped: {len(listings)}")
                    break
                
                if current_count == previously_counted:
                    retry_count += 1
                    print(f"Retry {retry_count}/{MAX_RETRIES} - Waiting for more results...", end='\r')
                    if retry_count >= MAX_RETRIES:
                        listings = page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).all()
                        print(f"\nArrived at all available or stalled.\nTotal Scraped: {len(listings)}")
                        break
                    page.wait_for_timeout(2000) # Wait a bit longer before next wheel
                else:
                    previously_counted = current_count
                    retry_count = 0 # Reset retry count if we found new items
                    print(
                        f"Currently Scraped: {current_count}", end='\r'
                    )

            business_list = BusinessList()

            # scraping
            for i, listing in enumerate(listings):
                try:
                    # OPTIMIZATION: Check URL before clicking
                    href = listing.get_attribute('href')
                    if href:
                         if href in global_seen_urls:
                             print(f"   Skipping known item {i+1} (Duplicate URL)...", end='\r')
                             continue
                    
                    listing.click()
                    page.wait_for_timeout(2000)
                    
                    print(f"Scraping {i+1}/{len(listings)}", end='\r')

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
                            # Wait briefly for it to be attached/visible
                            return loc.inner_text(timeout=timeout).strip()
                        except Exception:
                            return ""

                    # Name
                    try:
                        if page.locator(name_attribute).count() > 0:
                            business.name = page.locator(name_attribute).first.inner_text(timeout=5000).strip()
                        elif page.locator('h1').count() > 0:
                             # Fallback: find the first h1 that is NOT "Results"
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
                    # Add Metadata
                    business.scraped_query = search_for
                    business.scraped_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    if page.url:
                         global_seen_urls.add(page.url)

                    business_list.add_business(business)
                except Exception as e:
                    print(f'Error occurred: {e}')
            
            # output
            clean_filename = f"{search_for}".replace(' ', '_').replace(',', '').replace('\n', '')
            # business_list.save_to_excel(clean_filename) # Disable individual excel files per query for now
            
            # This will append to 'Gmaps Leads.csv'
            csv_path = business_list.save_to_csv(clean_filename) 
            print(f"\n   💾 Saved to main DB: {csv_path}")

            # 2. Upload if Online
            if online_mode and sheets_client:
                # sheets_utils now handles detailed logging
                try:
                        df = business_list.dataframe()
                        # Metadata already in DF from Business objects
                        
                        worksheet = sheets_utils.get_or_create_worksheet(sheets_client)
                        added, dupes = sheets_utils.upload_data_to_sheet(worksheet, df)
                        # Optional: Print simple confirmation if needed, but utils logs writing
                except Exception as e:
                    print(f"Failed: {e}")

        browser.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'Failed err: {e}')
