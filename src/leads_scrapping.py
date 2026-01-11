import datetime
from playwright.sync_api import sync_playwright

# Cross-platform interactive check
try:
    import msvcrt # Windows only
    IS_WINDOWS = True
except ImportError:
    IS_WINDOWS = False

# Import data models and helpers from sheets_utils
try:
    from .sheets_utils import Business, BusinessList, extract_coordinates_from_url, generate_unique_key
except ImportError:
    import sys
    print("Error: Could not import from sheets_utils.py. Make sure it is in the same directory.")
    sys.exit(1)

def scrape_data(page, search_for, total, existing_keys=None, known_names_sheet=None, known_names_local=None):
    """
    Scrapes data for a single query using the provided Playwright page.
    Args:
        existing_keys: set of 'Name|Phone' keys for final check.
        known_names_sheet: set of simplified lowercase names from Online Sheet.
        known_names_local: set of simplified lowercase names from Local CSVs.
    """
    print(f"\n🚀 STARTED SCRAPING: {search_for}")
    print(f"   Target: {total} leads")
    
    # Combined stats for log
    k_sheet = len(known_names_sheet) if known_names_sheet else 0
    k_local = len(known_names_local) if known_names_local else 0
    print(f"   Optimization: Checking against {k_sheet} online and {k_local} local records.")

    # Robust Search Box Locator for A/B Testing
    search_box = None
    selectors = [
        '//input[@id="searchboxinput"]', 
        '//input[@id="searchbox-input"]', 
        '//input[@aria-label="Search Google Maps"]',
        'input[name="q"]'
    ]
    
    for sel in selectors:
        if page.locator(sel).count() > 0:
            search_box = page.locator(sel).first
            break
            
    if search_box:
        search_box.fill(search_for)
    else:
        print("   ❌ CRITICAL: Could not find search box. Google layout might have changed.")
        return BusinessList()
        
    page.wait_for_timeout(2000)

    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)

    # --- VERIFICATION STEP ---
    print(f"\n   🔎 VERIFY SEARCH URL:")
    print(f"   {page.url}")
    if IS_WINDOWS:
         print("   Press Enter in terminal to confirm and start scrolling... ", end='')
         input()
    else:
         page.wait_for_timeout(3000) # Auto wait if not interactive
    # -------------------------

    # Check if results found
    try:
        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=5000)
    except:
        print("   ⚠️  No results found or page layout changed.")
        return BusinessList()

    previously_counted = 0
    feed_selector = 'div[role="feed"]'
    no_change_counter = 0
    MAX_NO_CHANGE = 150 # Increased to ~5 mins for 10k lists 
    
    # --- LIST COLLECTING LOOP ---
    print(f"   📜 Scrolling to load listings...")
    while True:
        # Check for "End of list" - Robust Checks
        # 1. Text based check (broad)
        if page.locator('//*[contains(text(), "reached the end of the list")]').count() > 0:
             print(f"   ✅ Reached end of list.")
             break
        
        # 2. Specific Class Marker (Google sometimes uses this)
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
                 msg = " [Press 's' to skip]" if IS_WINDOWS else ""
                 print(f"      ...waiting ({no_change_counter}/{MAX_NO_CHANGE}){msg}   ", end='\r')
            
            # Interactive Skip (Windows Only)
            if IS_WINDOWS and msvcrt.kbhit():
                key = msvcrt.getwch()
                if key.lower() == 's':
                    print("\n   ⏭️  Skipping wait (User Request). Proceeding.")
                    break

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
            
            if listing_name:
                check_name = listing_name.lower().strip()
                
                # Granular Checks
                if check_name:
                    if known_names_sheet and check_name in known_names_sheet:
                        print(f"      ⏭️  Skipping '{listing_name}' (Found in Google Sheet)")
                        skipped_count += 1
                        continue
                    
                    if known_names_local and check_name in known_names_local:
                        print(f"      ⏭️  Skipping '{listing_name}' (Found in Local DB)")
                        skipped_count += 1
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
            
            # --- SCOPED SCRAPING: SMART CONTEXT ---
            # Instead of looking for a generic role, we look for the H1 (Business Name) 
            # and then scope to its parent container to ensure we rely on the specific open panel.
            
            # 1. Wait for H1 (Validation of Load)
            name_attribute = 'h1.DUwDvf' 
            try:
                 # Wait globally first to ensure it's there
                 page.wait_for_selector(name_attribute, timeout=3000)
            except:
                 # Try fallback H1
                 try:
                     page.locator('h1').first.wait_for(timeout=2000)
                 except:
                     print(f"      ⚠️  Skip: No details load for #{i+1}")
                     continue

            # 2. Define Scope (Crucial for correct Extraction)
            # We assume the H1 is inside the Details Pane. 
            # We'll use the specific H1 we found to anchor our search.
            
            details_pane = page # Default fallback
            
            # Try to find the specific container holding this H1
            # Usually the details panel is a 'div[role="main"]' or has a specific class like 'm6QErb'
            if page.locator('div[role="main"]').count() > 0:
                # Gmaps often has multiple role="main" (e.g. Navigation, Search, Details)
                # The Details one is usually the last one opened or has specific attributes.
                # We iterate to find the one containing our target H1 (implicit or explicit check)
                
                # Heuristic: The one with the highest z-index or last in DOM is often the overlay.
                # Let's try the Last one first.
                details_pane = page.locator('div[role="main"]').last
            
            # Verify if H1 is inside this candidate `details_pane`
            if details_pane.locator(name_attribute).count() == 0 and details_pane.locator('h1').count() == 0:
                # If not found in the scoped pane, fallback to page (risky but necessary)
                # But to avoid "Stuck Ratings" (grabbing list view items), we try to get the H1's parent
                print("      ⚠️  Warning: Scoping issue. H1 not found in main pane. Using Page fallback.")
                details_pane = page

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
            
            # Reviews Logic (Improved)
            business.reviews_average = None
            business.reviews_count = None
            
            try:
                # Method 1: Robust Aria Label Scan (Stars)
                aria_selector = 'span[role="img"][aria-label*="stars"]'
                
                # Scan top 5 matches to find the one that likely belongs to the main header
                count_candidates = details_pane.locator(aria_selector).count()
                
                for i in range(min(5, count_candidates)):
                    lbl = details_pane.locator(aria_selector).nth(i).get_attribute('aria-label')
                    if not lbl: continue
                    
                    import re
                    # Example: "4.8 stars 153 Reviews" (Old format) or just "4.6 stars" (New format)
                    rating_match = re.search(r'(\d+(\.\d+)?) stars', lbl)
                    count_match = re.search(r'([\d,]+)\s+Review', lbl, re.IGNORECASE)
                    
                    if rating_match:
                         # Prioritize updating rating if found
                         if not business.reviews_average:
                             business.reviews_average = float(rating_match.group(1))

                    if count_match:
                         business.reviews_count = int(count_match.group(1).replace(',', ''))
                         break 
                
                # Method 1.5: Specific Review Count Element (New Google Maps Layout)
                # Found span[role="img" aria-label="113 reviews"] which is separate from stars
                if not business.reviews_count:
                    # Scan for any img role with "reviews" in label
                    review_spans = details_pane.locator('span[role="img"][aria-label*="reviews"]').all()
                    for span in review_spans[:3]: # check first few
                        lbl = span.get_attribute('aria-label')
                        # "113 reviews"
                        c_match = re.search(r'([\d,]+)\s+reviews', lbl, re.IGNORECASE)
                        if c_match:
                            business.reviews_count = int(c_match.group(1).replace(',', ''))
                            break
                    
                    # Method 1.6: Parens text fallback (e.g. "(113)") next to stars
                    # Sometimes no aria-label, but text is "(113)"
                    if not business.reviews_count and business.reviews_average:
                        # Try to find text matching (\d+) near the rating
                        # This is harder to target precisely, so we rely on checks above mostly.
                        pass

                # Method 2: Button Text Fallback (Specific for Count - e.g. "123 Reviews" button)
                if not business.reviews_count:
                    btn_xpath = '//button[contains(@aria-label, "Reviews")]'
                    if details_pane.locator(btn_xpath).count() > 0:
                        lbl = details_pane.locator(btn_xpath).first.get_attribute('aria-label')
                        count_match = re.search(r'([\d,]+)\s+Review', lbl, re.IGNORECASE)
                        if count_match:
                            business.reviews_count = int(count_match.group(1).replace(',', ''))
            except Exception: 
                pass

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
                # Helper to format count safely
                r_count = f"({business.reviews_count})" if business.reviews_count else ""
                print(f"      ✅  {business.name:<40} | 📞 {business.phone_number:<15} | ⭐ {business.reviews_average} {r_count}")
            else:
                 print(f"      ❌  {business.name:<40} | [DUPLICATE]")
            
        except Exception as e:
            print(f"      ⚠️  Error: {e}")

    print(f"\n   🏁 Finished. Scraped: {len(business_list.business_list)} | Skipped (Pre-Check): {skipped_count}")
    return business_list
