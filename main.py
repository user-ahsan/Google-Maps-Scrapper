# Made by user-ahsan
import datetime
from playwright.sync_api import sync_playwright
import argparse
import os
import sys
import subprocess

try:
    from fake_useragent import UserAgent
except ImportError:
    UserAgent = None

# Import Refactored Modules
try:
    from src import sheets_utils
    from src import leads_scrapping
    from src import db
    # from src import resource_utils # Optional utility
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
    
    def try_launch():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.google.com", timeout=10000)
            browser.close()
            
    try:
        try_launch()
        print("✅ PASS")
        browser_ready = True
    except Exception as e:
        print(f"\n   ⚠️  Browser Launch Failed: {e}")
        print("   🛠️  Attempting to auto-install Playwright binaries...")
        
        try:
            import subprocess
            # Install chromium specifically to keep size down
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("   ✅ Installation complete. Retrying launch...")
            
            try_launch()
            print("   ✅ PASS (Recovered)")
            browser_ready = True
            
        except Exception as install_error:
            print(f"   ❌ FATAL: Auto-install failed: {install_error}")
            print("   -> Tip: Run 'playwright install chromium' manually.")

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
    # NEW: Internal flag for self-installing browsers
    parser.add_argument("--install-browsers", action="store_true", help="INTERNAL: Run browser installer and exit")
    
    args = parser.parse_args()

    # --- SPECIAL MODE: BROWSER INSTALLATION ---
    if args.install_browsers:
        print(">>> STARTING INTERNAL BROWSER INSTALLER...")
        try:
            # If we are frozen, we must import playwright.__main__ and run it.
            if getattr(sys, 'frozen', False):
                from playwright.__main__ import main as pw_main
                # Hack sys.argv to be what playwright expects
                sys.argv = ["playwright", "install", "chromium"]
                pw_main()
            else:
                # In development, just run the command
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
                
            print(">>> INSTALLATION SUCCESSFUL")
            sys.exit(0)
        except Exception as e:
            print(f">>> INSTALLATION FAILED: {e}")
            sys.exit(1)
    # ------------------------------------------

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
    
    # 1. Local Data (DB init)
    print("   🧠 Initializing Local Database...", end=" ")
    from src import db
    db.init_db()
    # Migration Check
    csv_path = os.path.join('GMaps Data', 'Gmaps Leads.csv')
    db.import_csv_if_empty(csv_path)
    
    known_names_local = db.get_known_names()
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
        
        # Dynamic User Agent (Robust Fallback)
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        if UserAgent:
            try:
                # Force desktop to avoid mobile layouts which break selectors
                ua_gen = UserAgent(platforms='desktop')
                ua = ua_gen.random
                print(f"   🕵️  User-Agent: {ua}")
            except Exception as e:
                 print(f"   🕵️  User-Agent: {ua} (Fallback - Generator Error: {e})")
        else:
            print(f"   🕵️  User-Agent: {ua} (Fixed - Library Missing)")

        page = browser.new_page(locale="en-GB", user_agent=ua)

        page.goto("https://www.google.com/maps", timeout=20000)
        
        page.goto("https://www.google.com/maps", timeout=20000)
        
        for index, search_for in enumerate(search_list):
            try:
                print(f"\n-----\n🔎 Processing Query {index+1}/{len(search_list)}: {search_for}")

                # REFACTORED CALL: Delegate scraping to module
                # We pass existing keys helper if needed, but scrape_data mainly returns a list.
                # Real-time dedupe in scrape_data requires keys.
                
                # 1. Refresh Deduplication Data (Race Condition Fix)
                # We load this PER QUERY to ensure we know about data added by other instances/threads.
                print("   🔄 Refreshing local/online data for deduplication...", end=" ")
                
                # [DB] Use DB for fast local lookups
                # db imported at top-level
                known_names_local = db.get_known_names()
                
                known_names_sheet = set()
                existing_keys = set()
                
                if online_mode and worksheet:
                     # print("Fetching real-time existing records...")
                     existing_keys = sheets_utils.get_existing_keys(worksheet)
                     known_names_sheet = sheets_utils.get_all_known_names(worksheet, local_dir=None)
                
                print(f"[Done. Local (DB): {len(known_names_local)} | Online: {len(known_names_sheet)}]")

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
                
                # Save to DB & CSV
                # The business_list_obj.save_to_csv now might be deprecated or wrapped
                # For now let's use the new db method in leads_scrapping or manually here?
                # Ideally leads_scrapping returns the object, we save it.
                
                # We'll save to DB first
                print(f"   💾 Saving to Local Database...", end=" ")
                new_db_count = business_list_obj.save_to_db()
                print(f"Done (+{new_db_count} new).")
                
                # Save to CSV (Export)
                clean_filename = f"{search_for}".replace(' ', '_').replace(',', '').replace('\n', '')
                csv_path = business_list_obj.save_to_csv(clean_filename) # Appends to main file
                print(f"   📂 Exported to CSV: {csv_path}")


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
                break
            except Exception as query_error:
                print(f"\n❌ CRITICAL ERROR processing query '{search_for}': {query_error}")
                print("   ⚠️  Skipping to next query to prevent crash...")
                continue
        
        browser.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'Failed err: {e}')
