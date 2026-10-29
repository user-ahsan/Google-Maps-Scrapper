import os
import sys

# Ensure UTF-8 output encoding for emojis on Windows consoles
try:
    if sys.stdout:
        reconfig_stdout = getattr(sys.stdout, 'reconfigure', None)
        if callable(reconfig_stdout):
            reconfig_stdout(encoding='utf-8', errors='replace')
    if sys.stderr:
        reconfig_stderr = getattr(sys.stderr, 'reconfigure', None)
        if callable(reconfig_stderr):
            reconfig_stderr(encoding='utf-8', errors='replace')
except Exception:
    pass

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.leads_scraping import scrape_data


def test_headed_scrape():
    """
    Test scraping in headed (visible) mode with example query.
    Tests data extraction with 5 result limit.
    """
    print("="*60)
    print("   HEADED SCRAPING TEST (5 results, visible browser)")
    print("="*60)

    test_query = "Restaurants in Chicago"
    test_limit = 5

    if sys.stdin and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
        input("\nPress Enter to start headed test (browser will be visible)...")
    else:
        print("\n[AUTO] Non-interactive environment detected. Starting headed test automatically...")

    try:
        with sync_playwright() as p:
            print("1. Launching Browser (Headed)...")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            print("2. Navigate to Google Maps...")
            page.goto("https://www.google.com/maps", timeout=30000)

            print(f"3. Running scrape for: {test_query}")
            print("   (Browser is visible - you can watch the process)")

            business_list = scrape_data(
                page=page,
                search_for=test_query,
                total=test_limit,
                existing_keys=set(),
                known_names_sheet=None,
                known_names_local=None,
                auto_accept=True,
                controller=None,
                max_scroll_time=60,
                max_retries=3,
                scroll_wait=2000
            )

            print("\n4. Results:")
            print(f"   Total scraped: {len(business_list.business_list)}")
            print(f"   Expected limit: {test_limit}")

            if len(business_list.business_list) > 0:
                print("\n5. Data Validation:")
                for i, business in enumerate(business_list.business_list[:3], 1):
                    print(f"   {i}. {business.name}")
                    print(f"      Phone: {business.phone_number}")
                    print(f"      Address: {business.address}")
                    print(f"      Website: {business.website}")

                    # Validate required fields
                    errors = []
                    if not business.name:
                        errors.append("Missing name")
                    if not business.phone_number and not business.address:
                        errors.append("Missing contact info")

                    if errors:
                        print(f"      [WARN] Errors: {', '.join(errors)}")
                    else:
                        print("      [OK] Valid")
            else:
                print("\n   [WARN] No businesses scraped!")

            print("\n6. Waiting 5 seconds before closing...")
            import time
            time.sleep(5)

            print("\n7. Cleanup...")
            browser.close()

            if len(business_list.business_list) > 0:
                print("\n" + "="*60)
                print("[PASS] HEADED SCRAPE TEST PASSED")
                print("="*60)
            else:
                print("\n" + "="*60)
                print("[FAIL] HEADED SCRAPE TEST FAILED (no results)")
                print("="*60)
                raise Exception("No businesses scraped")

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        print("="*60)
        raise

if __name__ == "__main__":
    test_headed_scrape()
