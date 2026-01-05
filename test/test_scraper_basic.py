from playwright.sync_api import sync_playwright
import time

def test_scraper_basic():
    print("="*60)
    print("   SCRAPER MECHANICS TEST   ")
    print("="*60)
    
    query = "Coffee shops in New York"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print(f"1. Navigate to Google Maps...")
        page.goto("https://www.google.com/maps")
        page.wait_for_timeout(3000)
        
        print(f"2. Search for '{query}'...")
        page.locator('//input[@id="searchboxinput"]').fill(query)
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        
        print("3. checking results...")
        try:
             # Wait for at least one result
            page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=10000)
            listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
            count = len(listings)
            
            if count > 0:
                print(f"✅ Found {count} results immediately.")
            else:
                print("⚠️ No results found immediately (Count 0).")
                
        except Exception as e:
            print(f"❌ Error finding results: {e}")

        print("4. Test Scroll...")
        try:
            feed_selector = 'div[role="feed"]'
            if page.locator(feed_selector).count() > 0:
                 print("   Feed detected. Scrolling...")
                 page.locator(feed_selector).evaluate("node => node.scrollTop += 2000")
            else:
                 print("   Feed not found, using global scroll...")
                 page.mouse.wheel(0, 2000)
            
            page.wait_for_timeout(2000)
            listings_after = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
            print(f"   Count after scroll: {len(listings_after)}")
        except Exception as e:
            print(f"⚠️ Scroll test warning: {e}")

        browser.close()
        print("✅ Scraper Test Complete")

if __name__ == "__main__":
    test_scraper_basic()
