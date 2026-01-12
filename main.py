import datetime
from playwright.sync_api import sync_playwright
import argparse
import os
import sys
from fake_useragent import UserAgent

# Import Refactored Modules
try:
    from src import sheets_utils
    from src import leads_scrapping
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import modules: {e}")
    sys.exit(1)

# --- DIAGNOSTICS & SYNC ---

def run_diagnostics(force_offline=False):
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
    
    if force_offline:
        print("⏩ SKIPPED (Offline Mode Force)")
    else:
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

    print(f"   Synced with Sheets. Local file used.")

    # We use a FileLock here to prevent multiple scraper instances from 
    # trying to sync the SAME large CSV to Sheets at the exact same startup time.
    lock_path = os.path.join(base_dir, 'sync.lock')
    
    try:
        print("   🔒 Acquiring sync lock...", end=" ")
        with sheets_utils.FileLock(lock_path, timeout=5):
            print("Acquired.")
            
            import pandas as pd
            df = pd.read_csv(target_csv)
            if df.empty:
                print("   File is empty.")
                return
            
            print(f"   Syncing {os.path.basename(target_csv)}...", end=" ")
            added, dupe = sheets_utils.upload_data_to_sheet(worksheet, df)
            print(f"Done. (+{added}, {dupe} dupes)")
            
    except sheets_utils.TimeoutError:
         print("\n   ⚠️  Could not acquire sync lock (Another instance is syncing?). Skipping sync.")
    except Exception as e:
        print(f"   Error syncing {target_csv}: {e}")

def main():
    # read search from arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    parser.add_argument("-headed", "--headed", action="store_true", help="Run with browser visible")
    parser.add_argument("-m", "--manual", action="store_true", help="Enable manual verification prompt")
    parser.add_argument("-offline", "--offline", action="store_true", help="Force offline mode (Skip Sheets Sync)")
    args = parser.parse_args()

    # 1. Run Diagnostics
    browser_ok, sheets_client, online_mode = run_diagnostics(force_offline=args.offline)

    if not browser_ok:
        if not args.manual:
             pass # Auto-proceed if not manual mode
        else:
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
        if args.manual:
             resp = input("   Continue? (Y/n): ")
             if resp.lower() == 'n':
                 sys.exit()
    
    # --- OPTIMIZATION: Pre-load SEEN NAMES (Granular) ---
    known_names_sheet = set()
    known_names_local = set()
    
    # 1. Local Data (Always Load)
    print("   🧠 Loading Local DB for deduplication...", end=" ")
    known_names_local = sheets_utils.get_all_known_names(None, local_dir='GMaps Data')
    print(f"[{len(known_names_local)} records]")

    # 2. Online Data (If Online)
    worksheet = None
    if online_mode and sheets_client:
        worksheet = sheets_utils.get_or_create_worksheet(sheets_client)
        print("   🧠 Loading Sheet Data for deduplication...", end=" ")
        known_names_sheet = sheets_utils.get_all_known_names(worksheet, local_dir=None) 
        print(f"[{len(known_names_sheet)} records]")
    
    # Combined for global stats if needed, or just pass both
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
        browser = p.chromium.launch(headless=not args.headed)
        
        # Dynamic User Agent
        try:
            ua = UserAgent().random
            print(f"   🕵️  User-Agent: {ua}")
        except:
             ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
             print(f"   🕵️  User-Agent: {ua} (Fallback)")

        page = browser.new_page(locale="en-GB", user_agent=ua)

        page.goto("https://www.google.com/maps", timeout=20000)
        
        page.goto("https://www.google.com/maps", timeout=20000)
        
        try:
            for index, search_for in enumerate(search_list):
                print(f"\n-----\n🔎 Processing Query {index+1}/{len(search_list)}: {search_for}")

                # REFACTORED CALL: Delegate scraping to module
                # We pass existing keys helper if needed, but scrape_data mainly returns a list.
                # Real-time dedupe in scrape_data requires keys.
                
                # 1. Refresh Deduplication Data (Race Condition Fix)
                # We load this PER QUERY to ensure we know about data added by other instances/threads.
                print("   🔄 Refreshing local/online data for deduplication...", end=" ")
                known_names_local = sheets_utils.get_all_known_names(None, local_dir='GMaps Data')
                
                known_names_sheet = set()
                existing_keys = set()
                
                if online_mode and worksheet:
                     # print("Fetching real-time existing records...")
                     existing_keys = sheets_utils.get_existing_keys(worksheet)
                     known_names_sheet = sheets_utils.get_all_known_names(worksheet, local_dir=None)
                
                print(f"[Done. Local: {len(known_names_local)} | Online: {len(known_names_sheet)}]")

                # Scrape
                business_list_obj = leads_scrapping.scrape_data(
                    page, 
                    search_for, 
                    total, 
                    existing_keys, 
                    known_names_sheet=known_names_sheet, 
                    known_names_local=known_names_local,
                    auto_accept=not args.manual
                )
                
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

        except leads_scrapping.StopScrapingException:

            print("\n🛑 Execution Interrupted by User (Shift+Q). Stopping queues.")
        
        browser.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'Failed err: {e}')
