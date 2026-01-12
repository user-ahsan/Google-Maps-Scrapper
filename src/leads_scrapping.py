# Made by user-ahsan
import datetime
from playwright.sync_api import sync_playwright

# Cross-platform interactive check
try:
    import msvcrt # Windows only
    IS_WINDOWS = True
except ImportError:
    IS_WINDOWS = False
    import sys, tty, termios, select

    def unix_kbhit():
        dr, dw, de = select.select([sys.stdin], [], [], 0)
        return dr != []

    def unix_getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

# Import data models and helpers from sheets_utils
try:
    from .sheets_utils import Business, BusinessList, extract_coordinates_from_url, generate_unique_key
except ImportError:
    import sys
    print("Error: Could not import from sheets_utils.py. Make sure it is in the same directory.")
    sys.exit(1)

# --- CUSTOM EXCEPTIONS ---
class StopScrapingException(Exception):
    """Raised when the user wants to stop the entire scraping process."""
    pass

def scrape_data(page, search_for, total, existing_keys=None, known_names_sheet=None, known_names_local=None, auto_accept=False, controller=None, max_scroll_time=300, max_retries=5):
    """
    Scrapes data for a single query using the provided Playwright page.
    """
    print(f"\n🚀 STARTED SCRAPING: {search_for}")
    print(f"   Target: {total} leads | Limit: {max_scroll_time}s")
    
    # Combined stats for log
    k_sheet = len(known_names_sheet) if known_names_sheet else 0
    k_local = len(known_names_local) if known_names_local else 0
    print(f"   Optimization: Checking against {k_sheet} online and {k_local} local records.")

    # Robust Search Box Locator for A/B Testing
    search_box = None
    selectors = [
        'input[name="q"]',
        'input#searchboxinput', 
        'input#searchbox-input', 
        'input[aria-label="Search Google Maps"]',
    ]
    
    print("   🔍 Waiting for search box...", end=" ", flush=True)
    for _ in range(30): # Wait up to 30 seconds (checks every 1s)
        for sel in selectors:
            try:
                if page.locator(sel).count() > 0 and page.locator(sel).is_visible():
                    search_box = page.locator(sel).first
                    print(f"Found ({sel})")
                    break
            except: pass
        if search_box: break
        page.wait_for_timeout(1000)

    if search_box:
        try:
            search_box.click()
            search_box.fill(search_for)
        except Exception as e:
             print(f"\n   ❌ Error interacting with search box: {e}")
             return BusinessList()
    else:
        print("\n   ❌ CRITICAL: Could not find search box. Google layout might have changed.")
        return BusinessList()
        
    page.wait_for_timeout(2000)

    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)

    # --- VERIFICATION STEP ---
    print(f"\n   🔎 VERIFY SEARCH URL:")
    print(f"   {page.url}")
    if IS_WINDOWS and not auto_accept:
         print("   Press Enter in terminal to confirm and start scrolling... ", end='')
         input()
    elif auto_accept:
         print("   ⏩ Auto-accepting URL (Autonomous Mode)")
         page.wait_for_timeout(2000)
    else:
         page.wait_for_timeout(3000) 
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
    MAX_NO_CHANGE = int(max_retries) # From config
    
    start_time = time.time() # Start Timer

    # --- LIST COLLECTING LOOP ---
    print(f"   📜 Scrolling to load listings...")
    while True:
        # Check Timeout
        if (time.time() - start_time) > max_scroll_time:
            print(f"   ⚠️  Time limit reached ({max_scroll_time}s). Proceeding with current list.")
            break

        # Check for "End of list"
        if page.locator('//*[contains(text(), "reached the end of the list")]').count() > 0:
             print(f"   ✅ Reached end of list.")
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
                 msg = " [Press 's' to skip, 'q' to next, 'Shift+Q' to stop all]"
                 print(f"      ...Scrolling & Loading new results ({no_change_counter}/{MAX_NO_CHANGE}){msg}   ", end='\r')
            
            # Interactive Skip (Cross-Platform)
            key = None
            if IS_WINDOWS:
               if msvcrt.kbhit():
                   key = msvcrt.getwch()
            else:
               if unix_kbhit():
                   key = unix_getch()

            if key:
                if key.lower() == 's':
                    print("\n   ⏭️  Skipping wait (User Request). Proceeding.")
                    break
                elif key.lower() == 'q':
                    # ... logic same as before ...
                    if key == 'Q':
                         print("\n   🛑 HARD STOP (User Request). Stopping all queries...")
                         raise StopScrapingException("User pressed Shift+Q")
                    else:
                         print("\n   ⚠️  Quitting current query (User Request).")
                         return BusinessList()

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
        # --- CONTROLLER CHECK ---
        if controller:
            if controller.is_stopped():
                print("\n   🛑 STOP Signal Received. Exiting loop.")
                break
            
            if controller.is_paused():
                print(f"      ⏸️  Paused... Waiting for resume.", end='\r')
                controller.check_pause() # This BLOCKS until resumed
                print(f"      ▶️  Resumed!                   ")
        # ------------------------
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
                    display_name = (listing_name[:30] + '..') if len(listing_name) > 30 else listing_name
                    
                    if known_names_sheet and check_name in known_names_sheet:
                        print(f"   ⏭️ {display_name:<32} | [Found in Google Sheet]")
                        skipped_count += 1
                        continue
                    
                    if known_names_local and check_name in known_names_local:
                        print(f"   ⏭️ {display_name:<32} | [Found in Local DB]")
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
            
            # 1. Wait for H1 (Business Name) - Robust Check
            # We look for ANY h1 inside the main role, as class names change.
            try:
                # Scoping: Try to find the details pane first
                # The details pane usually has role="main" and contains an h1.
                # We prioritize the last opened one (highest z-index usually)
                candidates = page.locator('div[role="main"]').all()
                details_pane = None
                
                # Check candidates in reverse (newest first)
                for pane in reversed(candidates):
                     if pane.locator('h1').count() > 0:
                         details_pane = pane
                         break
                
                if not details_pane:
                    # Fallback to page if no specific pane found (e.g. mobile view or unique layout)
                    details_pane = page
                
                # Verify H1 exists
                details_pane.locator('h1').first.wait_for(timeout=3000)
            except Exception as e:
                print(f"      ⚠️  Skip: could not locate business details (H1 timeout). {e}")
                continue

            business = Business()
            business.scraped_query = search_for
            business.scraped_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            def safe_extract(locator_strategy, label, required=False):
                """
                Robust extraction with error logging.
                locator_strategy: lambda using details_pane to find element
                """
                try:
                    el = locator_strategy(details_pane)
                    if el.count() > 0:
                        return el.first.inner_text(timeout=1000).strip()
                except Exception as e:
                    # Log warning for ALL failures, not just required ones, but keep it clean
                    if required:
                         print(f"         ⚠️ Failed to extract {label}: {e}")
                    else:
                         # Optional Debug Log
                         # print(f"         ⚠️ (Optional) Failed to extract {label}")
                         pass
                return ""

            # Extract Data
            # Name
            business.name = safe_extract(lambda p: p.locator('h1'), "Name", required=True)
            if not business.name:
                business.name = check_name or "Unknown"

            # Address - Look for button with parsing data-item-id="address"
            # Removed brittle 'div[class*="fontBodyMedium"]' dependency. Using .first or smarter lookups.
            # Usually the text is the direct child or inside a structured div we can just grab text from.
            business.address = safe_extract(
                lambda p: p.locator('button[data-item-id="address"]'), 
                "Address"
            )

            # Website - Look for data-item-id="authority"
            web_text = safe_extract(
                lambda p: p.locator('a[data-item-id="authority"]'), 
                "Website"
            )
            if web_text:
                business.domain = web_text
                business.website = f"https://www.{web_text}" if not web_text.startswith('http') else web_text
            
            # Phone - Look for data-item-id="phone:tel:"
            business.phone_number = safe_extract(
                 lambda p: p.locator('button[data-item-id*="phone:tel:"]'),
                 "Phone"
            )
            
            # Reviews Logic (Improved)
            business.reviews_average = None
            business.reviews_count = None
            
            try:
                # Method 1: Robust Aria Label Scan (Stars)
                # Look for the stars aria label which is usually "X.X stars X Reviews" or similar
                aria_selector = 'span[role="img"][aria-label*="stars"]'
                
                # We try to find the one closest to the top of the details pane
                star_elements = details_pane.locator(aria_selector).all()
                
                for el in star_elements[:3]: # Check top 3
                    lbl = el.get_attribute('aria-label')
                    if not lbl: continue
                    
                    import re
                    # Patterns to extract "4.8" and "153"
                    rating_match = re.search(r'(\d+(\.\d+)?) stars', lbl)
                    
                    if rating_match:
                         if not business.reviews_average:
                             business.reviews_average = float(rating_match.group(1))

                    # Sometimes the count is in the same label, sometimes separate.
                    # If we found stars, look for "X Reviews" in text neighbors or siblings
                    # But often Google has a separate span for count now.
                    
                # Method 2: Explicit Review Count (often in a button or span with "reviews")
                # We look for text strictly matching number + "reviews" in appropriate container
                if not business.reviews_count:
                    # Look for button or span with specific text pattern
                    # "1,234 reviews" or "(1,234)"
                    
                    # 2a. Button check (common across layouts)
                    reviews_btn_lbl = safe_extract(
                        lambda p: p.locator('div[role="button"][aria-label*="reviews"]'), 
                        "Reviews Button Label"
                    ) # This gives text, but we want aria-label often.
                    
                    # Let's iterate elements with "reviews" in aria-label
                    candidates = details_pane.locator('[aria-label*="reviews"]').all()
                    for c in candidates[:5]:
                        lbl = c.get_attribute('aria-label')
                        count_match = re.search(r'([\d,]+)\s+Review', lbl, re.IGNORECASE)
                        if count_match:
                            business.reviews_count = int(count_match.group(1).replace(',', ''))
                            break
                            
                # Method 3: Fallback specific text extraction for count
                if not business.reviews_count and business.reviews_average:
                    # Try to find the text explicitly
                    # Often looks like: "4.8 (1,234)"
                    full_text = safe_extract(lambda p: p.locator('div[role="main"]'), "Full Text") # costly?
                    # No, let's look for known container classes or structure if possible.
                    # But since we want to avoid classes, let's rely on the stars element sibling.
                    pass 

            except Exception as e: 
                print(f"         ⚠️ Reviews Extraction Error: {e}")

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
            display_name = (business.name[:30] + '..') if len(business.name) > 30 else business.name
            
            if is_new:
                business_list.add_business(business)
                r_count = f"({business.reviews_count})" if business.reviews_count else ""
                # Compact single line format
                print(f"   ✅ {display_name:<32} | 📞 {business.phone_number:<15} | ⭐ {business.reviews_average} {r_count}")
            else:
                 print(f"   ❌ {display_name:<32} | [DUPLICATE]")
            
        except Exception as e:
            print(f"      ⚠️  Error: {e}")

    print(f"\n   🏁 Finished. Scraped: {len(business_list.business_list)} | Skipped (Pre-Check): {skipped_count}")
    return business_list
