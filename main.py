import datetime
from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
import os
import sys

@dataclass
class Business:
    """holds business data"""
    name: str = None
    address: str = None
    domain: str = None
    website: str = None
    phone_number: str = None
    category: str = None
    location: str = None
    reviews_count: int = None
    reviews_average: float = None
    latitude: float = None
    longitude: float = None
    google_maps_link: str = None
    
    def __hash__(self):
        """Make Business hashable for duplicate detection.
        Consider businesses different if:
        - Name is different, OR
        - Same name but different non-empty contact info (domain/website/phone)
        """
        # Create a tuple of fields that must match for duplicates
        # We'll include name plus any non-empty contact info fields
        hash_fields = [self.name]
        # Only include contact info fields if they're not empty
        if self.domain:
            hash_fields.append(f"domain:{self.domain}")
        if self.website:
            hash_fields.append(f"website:{self.website}")
        if self.phone_number:
            hash_fields.append(f"phone:{self.phone_number}")
        
        return hash(tuple(hash_fields))

@dataclass
class BusinessList:
    """holds list of Business objects,
    and save to both excel and csv
    """
    business_list: list[Business] = field(default_factory=list)
    _seen_businesses: set = field(default_factory=set, init=False)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    save_at = os.path.join('GMaps Data', today)
    # os.makedirs(save_at, exist_ok=True)  <-- REMOVED: Prevent auto-creation

    def add_business(self, business: Business):
        """Add a business to the list if it's not a duplicate based on key attributes"""
        business_hash = hash(business)
        if business_hash not in self._seen_businesses:
            self.business_list.append(business)
            self._seen_businesses.add(business_hash)
    
    def dataframe(self):
        """transform business_list to pandas dataframe

        Returns: pandas dataframe
        """
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file

        Args:
            filename (str): filename
        """
        os.makedirs(self.save_at, exist_ok=True)
        self.dataframe().to_excel(f"{self.save_at}/{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """saves pandas dataframe to csv file

        Args:
            filename (str): filename
        """
        os.makedirs(self.save_at, exist_ok=True)
        self.dataframe().to_csv(f"{self.save_at}/{filename}.csv", index=False)

def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """helper function to extract coordinates from url"""
    coordinates = url.split('/@')[-1].split('/')[0]
    # return latitude, longitude
    return float(coordinates.split(',')[0]), float(coordinates.split(',')[1])


def main():
    # read search from arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    parser.add_argument("-headed", "--headed", action="store_true", help="Run with browser visible")
    args = parser.parse_args()
    
    if args.search:
        search_list = [args.search]
        
    if args.total:
        total = args.total
    else:
        # if no total is passed, we set the value to random big number
        total = 1_000_000

    if not args.search:
        search_list = []
        # read search from input.txt file
        input_file_name = 'input.txt'
        # Get the absolute path of the file in the current working directory
        input_file_path = os.path.join(os.getcwd(), input_file_name)
        # Check if the file exists
        if os.path.exists(input_file_path):
        # Open the file in read mode
            with open(input_file_path, 'r') as file:
            # Read all lines into a list
                search_list = [line.strip() for line in file.readlines() if line.strip()]
                
        if len(search_list) == 0:
            print('Error occured: You must either pass the -s search argument, or add searches to input.txt')
            sys.exit()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        page = browser.new_page(locale="en-GB")

        page.goto("https://www.google.com/maps", timeout=20000)
        
        for search_for_index, search_for in enumerate(search_list):
            print(f"-----\n{search_for_index} - {search_for}")

            page.locator('//input[@id="searchboxinput"]').fill(search_for)
            page.wait_for_timeout(3000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)

            # scrolling
            page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

            previously_counted = 0
            retry_count = 0
            MAX_RETRIES = 5

            while True:
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(3000)

                current_count = page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).count()

                if current_count >= total:
                    listings = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).all()[:total]
                    listings = [listing.locator("xpath=..") for listing in listings]
                    print(f"Total Scraped: {len(listings)}")
                    break
                
                if current_count == previously_counted:
                    retry_count += 1
                    print(f"Retry {retry_count}/{MAX_RETRIES} - Waiting for more results...", end='\r')
                    if retry_count >= MAX_RETRIES:
                        listings = page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).all()
                        print(f"\nArrived at all available or stalled.\nTotal Scraped: {len(listings)}")
                        break
                    page.wait_for_timeout(2000) # Wait a bit longer before next wheel
                else:
                    previously_counted = current_count
                    retry_count = 0 # Reset retry count if we found new items
                    print(
                        f"Currently Scraped: {current_count}", end='\r'
                    )

            business_list = BusinessList()

            # scraping
            for i, listing in enumerate(listings):
                try:                        
                    listing.click()
                    page.wait_for_timeout(2000)
                    
                    print(f"Scraping {i+1}/{len(listings)}", end='\r')

                    name_attribute = 'h1.DUwDvf' 
                    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
                    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                    review_count_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//span'
                    reviews_average_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]' 
                                                           
                    business = Business()
                    
                    def get_text_safe(locator_xpath, timeout=3000):
                        try:
                            loc = page.locator(locator_xpath).first
                            # Wait briefly for it to be attached/visible
                            return loc.inner_text(timeout=timeout).strip()
                        except Exception:
                            return ""

                    # Name
                    try:
                        if page.locator(name_attribute).count() > 0:
                            business.name = page.locator(name_attribute).first.inner_text(timeout=5000).strip()
                        elif page.locator('h1').count() > 0:
                             # Fallback: find the first h1 that is NOT "Results"
                             all_h1s = page.locator('h1').all()
                             business.name = ""
                             for h1 in all_h1s:
                                 try:
                                     text = h1.inner_text(timeout=2000).strip()
                                     if text and "Results" not in text:
                                         business.name = text
                                         break
                                 except:
                                     continue
                        else:
                            business.name = ""
                    except:
                        business.name = ""

                    # Address
                    business.address = get_text_safe(address_xpath)

                    # Website
                    website_text = get_text_safe(website_xpath)
                    if website_text:
                        business.domain = website_text
                        business.website = f"https://www.{website_text}"
                    else:
                        business.domain = ""
                        business.website = ""

                    # Phone
                    business.phone_number = get_text_safe(phone_number_xpath)
                        
                    # Reviews Count
                    try:
                        if page.locator(review_count_xpath).count() > 0:
                            count_text = page.locator(review_count_xpath).first.inner_text(timeout=3000)
                            business.reviews_count = int(count_text.split()[0].replace(',', '').strip())
                        else:
                            business.reviews_count = None
                    except:
                         business.reviews_count = None
                        
                    # Reviews Average
                    try:
                        if page.locator(reviews_average_xpath).count() > 0:
                            avg_text = page.locator(reviews_average_xpath).first.get_attribute('aria-label', timeout=3000)
                            business.reviews_average = float(avg_text.split()[0].replace(',', '.').strip())
                        else:
                            business.reviews_average = None
                    except:
                        business.reviews_average = None
                
                    business.category = search_for.split(' in ')[0].strip()
                    business.location = search_for.split(' in ')[-1].strip()
                    business.latitude, business.longitude = extract_coordinates_from_url(page.url)
                    business.google_maps_link = page.url

                    business_list.add_business(business)
                except Exception as e:
                    print(f'Error occurred: {e}')
            
            # output
            clean_filename = f"{search_for}".replace(' ', '_').replace(',', '').replace('\n', '')
            business_list.save_to_excel(clean_filename)
            business_list.save_to_csv(clean_filename)

        browser.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'Failed err: {e}')
