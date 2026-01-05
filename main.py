import datetime
from playwright.sync_api import sync_playwright
import argparse
import os
import sys

# Import Refactored Modules
try:
    from src import sheets_utils
    from src import leads_scrapping
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import modules: {e}")
    sys.exit(1)

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
    
    sheets_client = sheets_utils.connect_to_sheets()
    if sheets_client:
        print("✅ PASS")
        online_mode = True
    else:
        print("⚠️ CHECK FAILED")
        print("   -> Could not connect to Google Sheets. Will run in OFFLINE mode.")

    print("-" * 50)
    return browser_ready, sheets_client, online_mode

def sync_offline_data(sheets_client):
    """Check for existing CSVs and upload them if possible."""
    print("\n☁️ Checking for offline data to sync...")
    
    base_dir = 'GMaps Data'
    target_csv = os.path.join(base_dir, 'Gmaps Leads.csv')
    
    if not os.path.exists(target_csv):
        print("   No 'Gmaps Leads.csv' found.")
        return

    print(f"   Found main CSV file. Syncing...")
    
    worksheet = sheets_utils.get_or_create_worksheet(sheets_client)
    if not worksheet:
        print("   Could not access worksheet for sync.")
        return

    try:
        import pandas as pd
        df = pd.read_csv(target_csv)
        if df.empty:
            print("   File is empty.")
            return
        
        print(f"   Syncing {os.path.basename(target_csv)}...", end=" ")
        added, dupe = sheets_utils.upload_data_to_sheet(worksheet, df)
        print(f"Done. (+{added}, {dupe} dupes)")
        
    except Exception as e:
        print(f"   Error syncing {target_csv}: {e}")

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

    if not browser_ok:
        if not args.yes:
             input("\n❌ Browser test failed. Check errors above. Press Enter to try anyway (or Ctrl+C to quit)...")
    
    if online_mode and sheets_client:
        # 2. Sync Offline Data
        sync_offline_data(sheets_client)
        
        # 3. Auto-Prune Duplicates (Maintenance)
        worksheet = sheets_utils.get_or_create_worksheet(sheets_client)
        if worksheet:
             sheets_utils.prune_duplicates(worksheet)
    else:
        print("\n⚠️ ORANGE ALERT: Running in OFFLINE MODE. Data will be saved to CSV only.")
        if not args.yes:
             resp = input("   Continue? (Y/n): ")
             if resp.lower() == 'n':
                 sys.exit()
    
    # --- OPTIMIZATION: Pre-load SEEN URLS & NAMES ---
    global_seen_urls = set()
    global_known_names = set()
    worksheet = None
    
    if online_mode and sheets_client:
        worksheet = sheets_utils.get_or_create_worksheet(sheets_client)
        # Load from both Online (if avail) and Offline
        # global_seen_urls = sheets_utils.get_all_seen_urls(worksheet) # (Optional if we use names optimization)
        global_known_names = sheets_utils.get_all_known_names(worksheet)
        print(f"   🧠 Loaded {len(global_known_names)} unique business names for instant skip.")
    elif not online_mode:
        # Load offline only
        global_known_names = sheets_utils.get_all_known_names(None)
        print(f"   🧠 Loaded {len(global_known_names)} unique business names (Offline) for instant skip.")
    # ----------------------------------------
    
    # Determine Search List
    search_list = []
    if args.search:
        search_list = [args.search]
    
    if not search_list:
        # read search from input.txt file
        input_file_name = 'input.txt'
        input_file_path = os.path.join(os.getcwd(), input_file_name)
        if os.path.exists(input_file_path):
            with open(input_file_path, 'r') as file:
                search_list = [line.strip() for line in file.readlines() if line.strip()]
                
        if len(search_list) == 0:
            print('Error occured: You must either pass the -s search argument, or add searches to input.txt')
            sys.exit()

    total = args.total if args.total else 1_000_000
    
    # 3. Start Orchestration
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        # User agent to ensure standard desktop view (fixes missing review counts)
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        page = browser.new_page(locale="en-GB", user_agent=ua)

        page.goto("https://www.google.com/maps", timeout=20000)
        
        for index, search_for in enumerate(search_list):
            print(f"\n-----\n🔎 Processing Query {index+1}/{len(search_list)}: {search_for}")

            # REFACTORED CALL: Delegate scraping to module
            # We pass existing keys helper if needed, but scrape_data mainly returns a list.
            # Real-time dedupe in scrape_data requires keys.
            
            existing_keys = set()
            if online_mode and worksheet:
                 print("   Fetching real-time existing records for deduplication...")
                 existing_keys = sheets_utils.get_existing_keys(worksheet)

            # Scrape
            # Scrape
            business_list_obj = leads_scrapping.scrape_data(page, search_for, total, existing_keys, global_known_names)
            
            # Save to CSV (Always)
            clean_filename = f"{search_for}".replace(' ', '_').replace(',', '').replace('\n', '')
            csv_path = business_list_obj.save_to_csv(clean_filename) # Appends to main file
            print(f"\n   💾 Saved to main DB: {csv_path}")

            # Upload to Sheets (If Online)
            if online_mode and worksheet:
                try:
                        df = business_list_obj.dataframe()
                        added, dupes = sheets_utils.upload_data_to_sheet(worksheet, df)
                        print(f"   ☁️  Upload complete: +{added} new, {dupes} duplicates.")
                except Exception as e:
                    print(f"Failed to upload: {e}")

        browser.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'Failed err: {e}')
