import os
import sys
import argparse
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent

# Import core modules
# Ensure src is in path if not already
sys.path.append(os.getcwd())

from src import sheets_utils
from src import leads_scrapping
from src import db

def run_gui_mode(input_file, creds_file, total=0, headless=True, controller=None, sheet_behavior="Append", max_scroll_time=300, max_retries=5):
    """
    Entry point for the GUI to run the scraper.
    """
    print(f"Starting Scraper in GUI Mode...")
    print(f"Input: {input_file}")
    print(f"Creds: {creds_file} (Checking...)")
    
    # 1. Setup Environment
    if os.path.exists(creds_file):
        # Override the global constant or pass it down?
        # sheets_utils.connect_to_sheets uses a param, so we pass it there.
        pass
    else:
        print(f"⚠️ Warning: Credentials file not found at {creds_file}")

    # 2. Diagnostics
    print("Running Diagnostics...", end=" ")
    sheets_client = sheets_utils.connect_to_sheets(credentials_file=creds_file)
    online_mode = (sheets_client is not None)
    print(f"Online Mode: {online_mode}")
    
    # 3. Setup Data
    db.init_db()
    known_names_local = db.get_known_names()
    known_names_sheet = set()
    worksheet = None
    
    if online_mode:
        # PASS BEHAVIOR
        worksheet = sheets_utils.get_or_create_worksheet(sheets_client, behavior=sheet_behavior)
        if worksheet:
            print("Loading Online Data...", end=" ")
            known_names_sheet = sheets_utils.get_all_known_names(worksheet)
            print(f"[{len(known_names_sheet)} records]")

    # 4. Read Search List
    search_list = []
    if os.path.exists(input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            search_list = [line.strip() for line in f.readlines() if line.strip()]
    
    if not search_list:
        print("❌ Error: No queries found in input file.")
        return

    # 5. Browser Launch
    with sync_playwright() as p:
        print(f"Launching Browser (Headless={headless})...")
        try:
            browser = p.chromium.launch(headless=headless)
        except Exception as e:
            print(f"❌ Failed to launch browser: {e}")
            print("Trying to install browsers...")
            import subprocess
            try:
                # Use sys.executable but safeguard in main_gui usually, 
                # but valid fallback if gui button didn't resolve it.
                env = os.environ.copy()
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"], env=env)
                browser = p.chromium.launch(headless=headless)
            except:
                 print("❌ Fatal Browser Error. Please use 'Re-Install Browsers' button.")
                 return

        ua = UserAgent(platforms='desktop').random
        page = browser.new_page(user_agent=ua, locale="en-GB")
        
        page.goto("https://www.google.com/maps", timeout=60000)

        # 6. Process Queries
        total_limit = total if total > 0 else 1_000_000
        
        for index, search_for in enumerate(search_list):
            # CONTROLLER CHECK (Outer Loop)
            if controller:
                if controller.is_stopped(): break
                if controller.is_paused(): controller.check_pause()

            try:
                print(f"\n[{index+1}/{len(search_list)}] Processing: {search_for}")
                
               # Refresh Dedupe Data per query
                known_names_local = db.get_known_names()
                existing_keys = set()
                if online_mode and worksheet:
                    existing_keys = sheets_utils.get_existing_keys(worksheet)
                    known_names_sheet = sheets_utils.get_all_known_names(worksheet)

                # Scrape
                business_list = leads_scrapping.scrape_data(
                    page, 
                    search_for, 
                    total_limit, 
                    existing_keys=existing_keys,
                    known_names_sheet=known_names_sheet,
                    known_names_local=known_names_local,
                    auto_accept=True, 
                    controller=controller,
                    max_scroll_time=max_scroll_time,
                    max_retries=max_retries
                )
                
                if controller and controller.is_stopped():
                    print("Aborting save due to stop signal.")
                    break

                # Save
                print("Saving results...")
                business_list.save_to_db()
                business_list.save_to_csv(search_for)
                
                if online_mode and worksheet:
                    df = business_list.dataframe()
                    sheets_utils.upload_data_to_sheet(worksheet, df)

            except Exception as e:
                print(f"❌ Error processing {search_for}: {e}")
                
        browser.close()
        print("✅ All queries completed.")
