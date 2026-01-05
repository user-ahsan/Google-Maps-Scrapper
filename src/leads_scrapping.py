import time
import datetime
from playwright.sync_api import sync_playwright

# Import data models and helpers from sheets_utils
try:
    from .sheets_utils import Business, BusinessList, extract_coordinates_from_url, generate_unique_key
except ImportError:
    import sys
    print("Error: Could not import from sheets_utils.py. Make sure it is in the same directory.")
    sys.exit(1)

def scrape_data(page, search_for, total, existing_keys=None, known_names=None):
    """
    Scrapes data for a single query using the provided Playwright page.
    Args:
        existing_keys: set of 'Name|Phone' keys for final check.
        known_names: set of simplified lowercase names for fast pre-check.
    """
    print(f"\n🚀 STARTED SCRAPING: {search_for}")
    print(f"   Target: {total} leads")
    if known_names:
        print(f"   Optimization: Checking against ~{len(known_names)} known names.")

    page.locator('//input[@id="searchboxinput"]').fill(search_for)
    page.wait_for_timeout(2000)

    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)

    # Check if results found
    try:
        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=5000)
    except:
        print("   ⚠️  No results found or page layout changed.")
        return BusinessList()

    previously_counted = 0
    feed_selector = 'div[role="feed"]'
    no_change_counter = 0
    MAX_NO_CHANGE = 20 
    
    # --- LIST COLLECTING LOOP ---
    print(f"   📜 Scrolling to load listings...")
    while True:
        # Check for "End of list"
        end_indicator = page.locator('//span[contains(text(), "You\'ve reached the end of the list")]')
        if end_indicator.count() > 0:
            print(f"   ✅ Reached end of list.")
            break
        
        if page.locator('span.HlvSq').count() > 0: 
            print(f"   ✅ Reached end of list (Marker).")
            break

        # Scroll
        if page.locator(feed_selector).count() > 0:
            page.locator(feed_selector).evaluate("node => node.scrollTop += 10000")
        else:
            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(2000)

        current_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()

        if total and current_count >= total:
            print(f"   🛑 Hit limit of {total}.")
            break
        
        if current_count == previously_counted:
            no_change_counter += 1
            if no_change_counter >= 5:
                 print(f"      ...waiting ({no_change_counter}/{MAX_NO_CHANGE})", end='\r')
            
            if no_change_counter >= MAX_NO_CHANGE:
                 print("\n   ⚠️  Max wait time reached. Proceeding.")
                 break
            page.wait_for_timeout(2000) 
        else:
            previously_counted = current_count
            no_change_counter = 0
            print(f"      Loaded: {current_count}...", end='\r')

    listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
    if total:
        listings = listings[:total]
    
    print(f"\n   🔍 Processing {len(listings)} Listings...")

    business_list = BusinessList()
    visited_urls = set()

    # --- DETAILED SCRAPING LOOP ---
    processed_count = 0
    skipped_count = 0
    
    for i, listing in enumerate(listings):
        try:
            # 1. OPTIMIZATION: Name Based Pre-Check
            # Try to get the name from aria-label or text BEFORE clicking
            listing_name = ""
            aria_label = listing.get_attribute('aria-label')
            if aria_label:
                listing_name = aria_label.split('·')[0].strip() # Often "Name · Rating"
            
            # Simple normalization for check
            check_name = listing_name.lower().strip()
            
            if known_names and check_name:
                # Basic check: exact match of name
                if check_name in known_names:
                    skipped_count += 1
                    # Minimal one-line log for skipped to keep console clean but alive
                    # print(f"      ⏭️  Skipped (Known): {listing_name}") 
                    continue
            
            # 2. Duplicate URL Check
            href = listing.get_attribute('href')
            if not href: continue
            if href in visited_urls: continue
            visited_urls.add(href)
            
            processed_count += 1
            
            # --- ACTION: CLICK & EXTRACT ---
            listing.click()
            page.wait_for_timeout(1500) # Short wait for panel
            
            details_pane = page.locator('div[role="main"]')
            if details_pane.count() == 0: details_pane = page

            # Validation: Wait for H1
            name_attribute = 'h1.DUwDvf' 
            try:
                 details_pane.locator(name_attribute).first.wait_for(timeout=3000)
            except:
                 # Try fallback H1
                 if details_pane.locator('h1').count() == 0:
                     print(f"      ⚠️  Skip: No details load for #{i+1}")
                     continue

            business = Business()
            business.scraped_query = search_for
            business.scraped_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            def get_text(xpath):
                try: return details_pane.locator(xpath).first.inner_text(timeout=2000).strip()
                except: return ""

            # Extract Data
            try:
                if details_pane.locator(name_attribute).count() > 0:
                    business.name = details_pane.locator(name_attribute).first.inner_text().strip()
                elif details_pane.locator('h1').count() > 0:
                    business.name = details_pane.locator('h1').first.inner_text().strip()
            except: business.name = check_name or "Unknown"

            business.address = get_text('//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]')
            
            web_text = get_text('//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]')
            if web_text:
                business.domain = web_text
                business.website = f"https://www.{web_text}"
            
            business.phone_number = get_text('//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]')
            
            # Reviews Logic (Simplified/Robust)
            try:
                aria_selector = 'span[role="img"][aria-label*="stars"]'
                if details_pane.locator(aria_selector).count() > 0:
                    lbl = details_pane.locator(aria_selector).first.get_attribute('aria-label')
                    import re
                    # "4.8 stars 153 Reviews"
                    rating_match = re.search(r'(\d+(\.\d+)?) stars', lbl)
                    count_match = re.search(r'([\d,]+)\s+Review', lbl, re.IGNORECASE)
                    
                    if rating_match: business.reviews_average = float(rating_match.group(1))
                    if count_match: business.reviews_count = int(count_match.group(1).replace(',', ''))
            except: pass

            business.category = search_for.split(' in ')[0].strip()
            business.location = search_for.split(' in ')[-1].strip()
            try:
                business.latitude, business.longitude = extract_coordinates_from_url(page.url)
            except: pass
            business.google_maps_link = page.url

            # Final Deep Deduplication (Keys)
            temp_key_data = {'Name': business.name, 'Phone Number': business.phone_number, 'Address': business.address}
            key = generate_unique_key(temp_key_data)
            
            is_new = True
            if existing_keys and key in existing_keys:
                is_new = False
            
            # --- BEAUTIFUL LOGGING ---
            if is_new:
                business_list.add_business(business)
                print(f"      ✅  {business.name:<40} | 📞 {business.phone_number:<15} | ⭐ {business.reviews_average}")
            else:
                 print(f"      ❌  {business.name:<40} | [DUPLICATE]")
            
        except Exception as e:
            print(f"      ⚠️  Error: {e}")

    print(f"\n   🏁 Finished. Scraped: {len(business_list.business_list)} | Skipped (Pre-Check): {skipped_count}")
    return business_list
