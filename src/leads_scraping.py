# Made by user-ahsan
import datetime
import time
from playwright.sync_api import sync_playwright

# Cross-platform interactive check
try:
    import msvcrt
    IS_WINDOWS = True
    IS_WINDOWS_VAR = msvcrt
except ImportError:
    IS_WINDOWS = False
    IS_WINDOWS_VAR = None
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
    from .selector_manager import SelectorManager
    from .logger import setup_logger
except ImportError:
    import sys
    print("Error: Could not import from sheets_utils.py. Make sure it is in the same directory.")
    sys.exit(1)

# --- CUSTOM EXCEPTIONS ---
class StopScrapingException(Exception):
    """Raised when the user wants to stop the entire scraping process."""
    pass

class RateLimiter:
    """Rate limiter with exponential backoff and jitter to avoid detection."""
    
    def __init__(self, base_delay=3.0, max_delay=30.0, jitter_pct=0.25):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_pct = jitter_pct
        self.request_count = 0
        self.consecutive_failures = 0
        self.current_delay = base_delay
    
    def wait(self, force_delay=None):
        """Wait with exponential backoff and jitter."""
        import time
        import random
        
        if force_delay:
            delay = force_delay
        else:
            # Add jitter to avoid detection patterns
            jitter = self.current_delay * self.jitter_pct
            delay = self.current_delay + random.uniform(-jitter, jitter)
        
        delay = max(0.5, min(delay, self.max_delay))
        time.sleep(delay)
    
    def record_success(self):
        """Reset delay after successful request."""
        self.consecutive_failures = 0
        self.current_delay = self.base_delay
    
    def record_failure(self):
        """Increase delay with exponential backoff after failure."""
        self.consecutive_failures += 1
        self.current_delay = min(self.base_delay * (2 ** self.consecutive_failures), self.max_delay)
        self.request_count += 1

def scrape_data(page, search_for, total, existing_keys=None, known_names_sheet=None, known_names_local=None, auto_accept=False, controller=None, max_scroll_time=300, max_retries=5, scroll_wait=3000, scroll_amount_per_step=10000, auto_skip_timeout=0, smart_wait_enabled=True, use_feed_scroll=True, pre_filter_names=True, show_progress=True, interactive_controls=True):
    """
    Scrapes data for a single query using the provided Playwright page.
    """
    print(f"\n[INFO] STARTED SCRAPING: {search_for}")
    scroll_mode = "feed" if use_feed_scroll else "global"
    print(f"   Target: {total} leads | Limit: {max_scroll_time}s | Scroll: {scroll_amount_per_step}px/step | Wait: {scroll_wait}ms | Mode: {scroll_mode} | Smart: {smart_wait_enabled}")

    # --- SETUP UTILS ---
    selector_manager = SelectorManager()
    logger = setup_logger()
    logger.info(f"Start Scraping: {search_for} (Target: {total})")
    
    # Initialize rate limiter for Google Maps requests
    rate_limiter = RateLimiter(base_delay=float(scroll_wait) / 1000.0, max_delay=30.0)
    
    # Combined stats for log
    k_sheet = len(known_names_sheet) if known_names_sheet else 0
    k_local = len(known_names_local) if known_names_local else 0
    print(f"   Optimization: Checking against {k_sheet} online and {k_local} local records.")

    # Robust Search Box Locator for A/B Testing
    search_box = None
    selectors = selector_manager.get("search_box")
    
    print("   [SEARCH] Waiting for search box...", end=" ", flush=True)
    
    search_box = None
    selectors = selector_manager.get("search_box")
    
    for _ in range(30):
        for sel in selectors:
            try:
                if page.locator(sel).count() > 0 and page.locator(sel).is_visible():
                    search_box = page.locator(sel).first
                    print(f"Found ({sel})")
                    break
            except:
                pass
        if search_box:
            break
        page.wait_for_timeout(1000)

    if search_box:
        try:
            search_box.click()
            search_box.fill(search_for)
            rate_limiter.wait()
            rate_limiter.record_success()
        except (ElementHandleError, TimeoutError) as e:
            logger.error(f"Error interacting with search box: {e}")
            print(f"   [ERROR] Error interacting with search box: {e}")
            rate_limiter.record_failure()
            return BusinessList()
    else:
        print("\n   [ERROR] CRITICAL: Could not find search box. Google layout might have changed.")
        logger.error("CRITICAL: Could not find search box. Layout changed.")
        return BusinessList()

        
    page.wait_for_timeout(2000)

    page.keyboard.press("Enter")
    rate_limiter.wait()
    rate_limiter.record_success()
    page.wait_for_timeout(4000)

    # --- VERIFICATION STEP ---
    print(f"\n   [VERIFY] VERIFY SEARCH URL:")
    print(f"   {page.url}")
    if IS_WINDOWS and not auto_accept:
         print("   Press Enter in terminal to confirm and start scrolling... ", end='')
         input()
    elif auto_accept:
         print("   [AUTO] Auto-accepting URL (Autonomous Mode)")
         page.wait_for_timeout(2000)
    else:
         page.wait_for_timeout(3000) 
    # -------------------------

    # Check if results found
    try:
        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=5000)
    except:
        print("   [WARN] No results found or page layout changed.")
        return BusinessList()

    previously_counted = 0
    feed_selector = selector_manager.get('feed')
    no_change_counter = 0
    MAX_NO_CHANGE = int(max_retries) # From config
    
    start_time = time.time() # Start Timer

    # --- LIST COLLECTING LOOP ---
    print(f"   [SCROLL] Scrolling to load listings...")
    while True:
        # Check Timeout
        if (time.time() - start_time) > max_scroll_time:
            print(f"   [WARN] Time limit reached ({max_scroll_time}s). Proceeding with current list.")
            break

        # Check for "End of list"
        if page.locator('//*[contains(text(), "reached the end of the list")]').count() > 0:
             print(f"   [DONE] Reached end of list.")
             break
        
        # Scroll
        if use_feed_scroll and page.locator(feed_selector).count() > 0:
            page.locator(feed_selector).evaluate(f"node => node.scrollTop += {scroll_amount_per_step}")
        else:
            page.mouse.wheel(0, scroll_amount_per_step)
        
        rate_limiter.wait()
        rate_limiter.record_success()
             
        if smart_wait_enabled:
            page.wait_for_timeout(scroll_wait)
        else:
            page.wait_for_timeout(scroll_wait)
        
        current_count = page.locator(selector_manager.get('listings')).count()
        
        if total and current_count >= total:
            print(f"   [STOP] Hit limit of {total}.")
            break
        
        if auto_skip_timeout > 0 and (time.time() - start_time) > auto_skip_timeout:
            print(f"   [SKIP] Auto-skip timeout reached ({auto_skip_timeout}s). Proceeding.")
            break
        
        if current_count == previously_counted:
            no_change_counter += 1
            if no_change_counter >= 5:
                 msg = " [Press 's' to skip, 'q' to next, 'Shift+Q' to stop all]"
                 # print(f"      ...Scrolling & Loading new results ({no_change_counter}/{MAX_NO_CHANGE}){msg}   ", end='\r')
            
            # Interactive Skip (Cross-Platform)
            key = None
            if interactive_controls:
                if IS_WINDOWS:
                    if msvcrt.kbhit():
                        key = msvcrt.getwch()
                else:
                    if unix_kbhit():
                        key = unix_getch()

                if key:
                    if key.lower() == 's':
                        print("\n   [SKIP] Skipping wait (User Request). Proceeding.")
                        break
                    elif key.lower() == 'q':
                        if key == 'Q':
                            print("\n   [STOP] HARD STOP (User Request). Stopping all queries...")
                            raise StopScrapingException("User pressed Shift+Q")
                        else:
                            print("\n   [QUIT] Quitting current query (User Request).")
                            return BusinessList()

            if controller and controller.is_skipped():
                 print("\n   [SKIP] Skip Signal Received. Moving to next query...")
                 break

            if no_change_counter >= MAX_NO_CHANGE:
                 print("\n   [WARN] Max wait time reached. Proceeding.")
                 break
            page.wait_for_timeout(scroll_wait) 
        else:
            previously_counted = current_count
            no_change_counter = 0
            # print(f"      Loaded: {current_count}...", end='\r')

    listings = page.locator(selector_manager.get('listings')).all()
    if total:
        listings = listings[:total]
    
    print(f"\n   [PROCESS] Processing {len(listings)} Listings...")

    business_list = BusinessList()
    visited_urls = set()

    # --- DETAILED SCRAPING LOOP ---
    processed_count = 0
    skipped_count = 0
    
    for i, listing in enumerate(listings):
        # --- CONTROLLER CHECK ---
        if controller:
            if controller.is_stopped():
                print("\n   [STOP] STOP Signal Received. Exiting loop.")
                break
            
            if controller.is_paused():
                print(f"      [PAUSE] Paused... Waiting for resume.")
                controller.check_pause() # This BLOCKS until resumed
                print(f"      [RESUME] Resumed!                   ")
        # ------------------------
        try:
            listing_name = ""
            check_name = ""

            if pre_filter_names:
                # 1. OPTIMIZATION: Name Based Pre-Check
                # Try to get the name from aria-label or text BEFORE clicking
                aria_label = listing.get_attribute('aria-label')
                if aria_label:
                    from .sheets_utils import clean_text_for_csv
                    raw_name = aria_label.split('·')[0].strip()
                    listing_name = clean_text_for_csv(raw_name)
                 
                # Simple normalization for check
                check_name = listing_name.lower().strip() if listing_name else ""
                  
                # Granular Checks
                if check_name:
                    display_name = (listing_name[:30] + '..') if len(listing_name) > 30 else listing_name
                    
                    if known_names_sheet and check_name in known_names_sheet:
                        print(f"   [SKIP] {display_name:<32} | [Found in Google Sheet]")
                        skipped_count += 1
                        continue
                    
                    if known_names_local and check_name in known_names_local:
                        print(f"   [SKIP] {display_name:<32} | [Found in Local DB]")
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
            rate_limiter.wait()
            rate_limiter.record_success()
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
                candidates = page.locator(selector_manager.get('details_pane')).all()
                details_pane = None
                
                # Check candidates in reverse (newest first)
                for pane in reversed(candidates):
                     if pane.locator(selector_manager.get('business_name')).count() > 0:
                         details_pane = pane
                         break
                
                if not details_pane:
                    # Fallback to page if no specific pane found (e.g. mobile view or unique layout)
                    details_pane = page
                
                # Verify H1 exists
                details_pane.locator(selector_manager.get('business_name')).first.wait_for(timeout=3000)
            except Exception as e:
                print(f"      [SKIP] Skip: could not locate business details (H1 timeout). {e}")
                logger.warning(f"Skip: H1 Timeout: {e}")
                continue

            business = Business()
            business.scraped_query = search_for
            business.scraped_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


            def safe_extract(locator_strategy, label, required=False):
                """
                Robust extraction with error logging.
                locator_strategy: lambda using details_pane to find element
                """
                try:
                    el = locator_strategy(details_pane)
                    if el.count() > 0:
                        raw_text = el.first.inner_text(timeout=1000).strip()
                        # Import and use cleaning function
                        from .sheets_utils import clean_text_for_csv
                        return clean_text_for_csv(raw_text)
                except Exception as e:
                    # Log warning for ALL failures, not just required ones, but keep it clean
                    if required:
                         print(f"         [WARN] Failed to extract {label}: {e}")
                    else:
                         # Optional Debug Log
                         # print(f"         [WARN] (Optional) Failed to extract {label}")
                         pass
                return ""


            # Method 3: Fallback specific text extraction for count
            # Extract Data
            # Name
            business.name = safe_extract(lambda p: p.locator(selector_manager.get('business_name')), "Name", required=True)
            if not business.name:
                business.name = check_name or "Unknown"

            # Address - Look for button with parsing data-item-id="address"
            # Removed brittle 'div[class*="fontBodyMedium"]' dependency. Using .first or smarter lookups.
            # Usually the text is the direct child or inside a structured div we can just grab text from.
            business.address = safe_extract(
                lambda p: p.locator(selector_manager.get('address_button')), 
                "Address"
            )

            # Website - Look for data-item-id="authority"
            web_text = safe_extract(
                lambda p: p.locator(selector_manager.get('website_link')), 
                "Website"
            )
            if web_text:
                business.domain = web_text
                business.website = f"https://www.{web_text}" if not web_text.startswith('http') else web_text
            
            # Phone - Look for data-item-id="phone:tel:"
            business.phone_number = safe_extract(
                 lambda p: p.locator(selector_manager.get('phone_button')),
                 "Phone"
            )
            
            # Reviews Logic (Improved)
            business.reviews_average = None
            business.reviews_count = None
            
            try:
                # Method 1: Robust Aria Label Scan (Stars)
                # Look for the stars aria label which is usually "X.X stars X Reviews" or similar
                aria_selector = selector_manager.get('stars_aria')
                
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
                    # 2a. Button check (common across layouts)
                    reviews_btn_lbl = safe_extract(
                        lambda p: p.locator(selector_manager.get('reviews_button')), 
                        "Reviews Button Label"
                    ) # This gives text, but we want aria-label often.
                    
                    # Let's iterate elements with "reviews" in aria-label
                    candidates = details_pane.locator(selector_manager.get('reviews_generic')).all()
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
                print(f"         [WARN] Reviews Extraction Error: {e}")

            # Extract actual category from business details (if available)
            # Category is often in buttons or spans near the business name
            business.category = safe_extract(
                lambda p: p.locator(selector_manager.get('category_button')),
                "Category"
            )
            # Fallback to query parsing if no category found
            if not business.category:
                business.category = search_for.split(' in ')[0].strip() if ' in ' in search_for else search_for
            
            # Location from query (this is the search location, which is acceptable)
            business.location = search_for.split(' in ')[-1].strip() if ' in ' in search_for else search_for
            
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
             
            if show_progress:
                # Clean display name for console safety
                safe_name = business.name.encode('ascii', 'ignore').decode('ascii')
                display_name = (safe_name[:30] + '..') if len(safe_name) > 30 else safe_name
                
                if is_new:
                    r_count = f"({business.reviews_count})" if business.reviews_count else ""
                    print(f"   [OK] {display_name:<32} | Phone: {business.phone_number:<15} | Rating: {business.reviews_average} {r_count}")
                else:
                    print(f"   [DUP] {display_name:<32} | [DUPLICATE]")
            
            if is_new:
                business_list.add_business(business)
            
        except Exception as e:
            print(f"      [ERROR] Warning: {e}")
            logger.error(f"Error processing listing: {e}")

    print(f"\n   [DONE] Finished. Scraped: {len(business_list.business_list)} | Skipped (Pre-Check): {skipped_count}")
    logger.info(f"Finished scraping {search_for}. Total: {len(business_list.business_list)}")
    return business_list
