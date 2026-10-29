import os
import sys

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.leads_scraping import dismiss_consent_dialog
from src.selector_manager import SelectorManager


def test_scraper_basic():
    print("="*60)
    print("   SCRAPER MECHANICS TEST   ")
    print("="*60)

    query = "Coffee shops in New York"
    selector_mgr = SelectorManager()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("1. Navigate to Google Maps...")
        page.goto("https://www.google.com/maps", timeout=30000)
        page.wait_for_timeout(2000)

        # Dismiss any consent dialog if present
        dismiss_consent_dialog(page)

        print(f"2. Search for '{query}'...")
        search_box = None
        search_selectors = selector_mgr.get("search_box") or []
        if isinstance(search_selectors, str):
            search_selectors = [search_selectors]

        for sel in search_selectors:
            try:
                if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                    search_box = page.locator(sel).first
                    print(f"   Found search box with selector: {sel}")
                    break
            except Exception:
                pass

        if not search_box:
            raise RuntimeError("Search box element could not be found.")

        search_box.fill(query)
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)

        print("3. checking results...")
        listings_sel = str(selector_mgr.get("listings") or '//a[contains(@href, "https://www.google.com/maps/place")]')
        try:
            # Wait for at least one result
            page.wait_for_selector(listings_sel, timeout=15000)
            listings = page.locator(listings_sel).all()
            count = len(listings)

            if count > 0:
                print(f"✅ Found {count} results immediately.")
            else:
                print("⚠️ No results found immediately (Count 0).")

        except Exception as e:
            print(f"❌ Error finding results: {e}")
            raise

        print("4. Test Scroll...")
        try:
            feed_selector = str(selector_mgr.get("feed") or 'div[role="feed"]')
            if page.locator(feed_selector).count() > 0:
                 print("   Feed detected. Scrolling...")
                 page.locator(feed_selector).first.evaluate("node => node.scrollTop += 2000")
            else:
                 print("   Feed not found, using global scroll...")
                 page.mouse.wheel(0, 2000)

            page.wait_for_timeout(2000)
            listings_after = page.locator(listings_sel).all()
            print(f"   Count after scroll: {len(listings_after)}")
        except Exception as e:
            print(f"⚠️ Scroll test warning: {e}")

        browser.close()
        print("✅ Scraper Test Complete")

if __name__ == "__main__":
    test_scraper_basic()
