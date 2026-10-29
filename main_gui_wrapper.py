import os
import sys

from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright

# Import core modules
# Ensure src is in path if not already
sys.path.append(os.getcwd())

from src import db, leads_scraping, sheets_utils
from src.job_manager import JobManager


def run_gui_mode(input_queries=None, input_file=None, creds_file=None, total=0, headless=True, export_csv=True, controller=None, sheet_behavior="Append", max_scroll_time=300, max_retries=5, resume=False, stats_queue=None, scroll_wait=3000, scroll_amount_per_step=10000, auto_skip_timeout=0, smart_wait_enabled=True, use_feed_scroll=True, export_sheets=True, export_db=True, auto_upload=False, auto_accept=True, manual_verification=False, interactive_controls=True, show_progress=True, pre_filter_names=True, batch_db_ops=True, cache_sheet_data=True):
    """
    Entry point for the GUI to run the scraper.
    """
    print("Starting Scraper in GUI Mode...")

    # --- 0. Job Manager Init ---
    job_manager = JobManager()
    search_list = []

    # --- 1. Resolve Queries ---
    if resume:
        if job_manager.has_unfinished_job():
            print(">>> RESUMING PREVIOUS JOB...")
            search_list = job_manager.get_pending_queries()
            if not search_list:
                print(">>> Job was marked incomplete but has no pending queries. Starting fresh.")
                resume = False # Fallback
        else:
            print(">>> No unfinished job to resume. Starting fresh.")
            resume = False

    if not resume:
        # Resolve fresh input
        if input_queries and isinstance(input_queries, list) and len(input_queries) > 0:
            search_list = input_queries
            print(f"Loaded {len(search_list)} queries from Direct Input.")
        elif input_file and os.path.exists(input_file):
            print(f"Reading from Input File: {input_file}")
            with open(input_file, encoding='utf-8') as f:
                search_list = [line.strip() for line in f if line.strip()]

        # Start Tracking
        if search_list:
            job_manager.start_new_job(search_list)
        else:
            print("❌ Error: No queries provided (File or Direct Input empty).")
            return

    # --- 2. Environment & Diagnostics ---
    if creds_file and os.path.exists(creds_file):
        print(f"Creds: {creds_file}")
    else:
        if creds_file:
            print(f"⚠️ Warning: Credentials file not found at {creds_file}")

    print("Running Diagnostics...", end=" ")
    sheets_client = sheets_utils.connect_to_sheets(credentials_file=creds_file)
    online_mode = (sheets_client is not None)
    print(f"Online Mode: {online_mode}")

    # --- 3. Setup Data ---
    db.init_db()

    worksheet = None
    if online_mode:
        worksheet = sheets_utils.get_or_create_worksheet(sheets_client, behavior=sheet_behavior)
        if worksheet:
            print("Connected to Google Sheet.")

    # --- 4. Browser Launch ---
    with sync_playwright() as p:
        print(f"Launching Browser (Headless={headless})...")
        try:
            browser = p.chromium.launch(headless=headless)
        except Exception as e:
            print(f"❌ Failed to launch browser: {e}")
            print("Trying to install browsers...")
            import subprocess
            try:
                env = os.environ.copy()
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"], env=env)
                browser = p.chromium.launch(headless=headless)
            except Exception:
                 print("❌ Fatal Browser Error. Please use 'Re-Install Browsers' button.")
                 return

        from src.config_manager import ConfigManager
        config = ConfigManager().get_config()
        stored_ua = config.get("user_agent", "")
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        if stored_ua and ("Mobile" not in stored_ua and "iPhone" not in stored_ua and "Android" not in stored_ua):
            ua = stored_ua
        elif UserAgent:
            try:
                ua = UserAgent(platforms='pc').random
            except Exception:
                pass

        page = browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent=ua,
            locale="en-GB"
        )
        page.goto("https://www.google.com/maps", timeout=60000)

        # --- 5. Process Queries ---
        total_limit = total if total > 0 else 1_000_000

        # We work on a copy or index, but JobManager tracks strings.
        # Since we might have resumed, search_list is already the pending list.

        # Create a safe iteration list
        current_batch = list(search_list) # Work on copy

        for index, search_for in enumerate(current_batch):
            # CONTROLLER CHECK (Outer Loop)
            if controller:
                if controller.is_stopped():
                    break
                if controller.is_paused():
                    controller.check_pause()

            try:
                print(f"\n[{index+1}/{len(current_batch)}] Processing: {search_for}")

               # Refresh Dedupe Data per query
                known_names_local = db.get_known_names()
                existing_keys = set()
                known_names_sheet = set()
                if online_mode and worksheet:
                    existing_keys = sheets_utils.get_existing_keys(worksheet)
                    known_names_sheet = sheets_utils.get_all_known_names(worksheet)

                # Scrape
                business_list = leads_scraping.scrape_data(
                    page=page,
                    search_for=search_for,
                    total=total_limit,
                    existing_keys=existing_keys,
                    known_names_sheet=known_names_sheet,
                    known_names_local=known_names_local,
                    auto_accept=auto_accept,
                    controller=controller,
                    max_scroll_time=max_scroll_time,
                    max_retries=max_retries,
                    scroll_wait=scroll_wait,
                    scroll_amount_per_step=scroll_amount_per_step,
                    auto_skip_timeout=auto_skip_timeout,
                    smart_wait_enabled=smart_wait_enabled,
                    use_feed_scroll=use_feed_scroll,
                    pre_filter_names=pre_filter_names,
                    show_progress=show_progress,
                    interactive_controls=interactive_controls
                )

                # Update Job Manager Stats
                leads_count = len(business_list.business_list)
                job_manager.update_leads_count(leads_count)

                # Emit Stats to GUI
                if stats_queue:
                    stats_queue.put({
                        "type": "stats_update",
                        "total_leads": job_manager.current_state["total_leads_found"],
                        "completed": len(job_manager.current_state["completed_queries"]),
                        "total_queries": len(job_manager.current_state["pending_queries"]) + len(job_manager.current_state["completed_queries"])
                    })

                if controller and controller.is_stopped():
                    print("Aborting save due to stop signal.")
                    break

                # Save
                print("Saving results...", end=" ")
                if export_db:
                    db_count = business_list.save_to_db()
                    print(f"Local (+{db_count})", end=" ")

                # Conditionally save to CSV
                if export_csv:
                    business_list.save_to_csv(search_for)
                    print("| CSV ✓", end=" ")

                if export_sheets and online_mode and worksheet:
                    df = business_list.dataframe()
                    added, _ = sheets_utils.upload_data_to_sheet(worksheet, df)
                    print(f"| Cloud (+{added})")
                else:
                    print()

                # Mark Complete
                job_manager.mark_query_complete(search_for)

            except leads_scraping.StopScrapingException:
                print("\n🛑 Execution Interrupted by User. Stopping queries.")
                break
            except Exception as e:
                print(f"❌ Error processing {search_for}: {e}")
                # We do NOT mark as complete so it is retried next time

        browser.close()

        # If we finished the loop normally and no stop signal
        if controller and not controller.is_stopped():
            print("✅ All queries completed.")
            job_manager.set_status("COMPLETED")
            job_manager.clear_job() # Optional: clean up file
        else:
             print("⚠️ Stopped by User.")
             job_manager.set_status("STOPPED")
