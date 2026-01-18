# Leads Scraping Logic (`src/leads_scraping.py`)

## 📝 Overview
This file contains the core engine of the Google Maps Scraper. It utilizes **Playwright** to automate a Chromium browser instance, interacting with the Google Maps interface to search, scroll, and extract business details.

## ⚙️ Key Functions

### `scrape_data(page, search_for, total, ...)`
The main entry point for the scraping process.
-   **Inputs**:
    -   `page`: The Playwright page object.
    -   `search_for`: The search query string (e.g., "Restaurants in NYC").
    -   `total`: Target number of leads to scrape.
    -   `known_names_*`: Sets of existing data for deduplication.
-   **Workflow**:
    1.  Validates and sanitizes the search query.
    2.  Navigates to Google Maps.
    3.  Types the query and presses Enter.
    4.  Waits for the "Feed" (the list of results) to load.
    5.  Enters the **Scraping Loop**:
        -   Extracts data from visible cards using generic selectors.
        -   Scrolls the feed panel to load more results.
        -   Checks for end-of-list indicators.
        -   Deduplicates against known names in real-time.
    6.  Returns a `BusinessList` object containing valid `Business` dataclass instances.

### `extract_business_data(card_locator)`
Extracts raw text from a single business card in the feed.
-   **Strategy**: Uses XPaths to find `aria-label` or specific text nodes for Name, Rating, Reviews, and Phone.
-   **Robustness**: Uses `try-except` blocks for optional fields (like Phone or Website) to prevent crashing on incomplete listings.

## 🔧 Selectors & Heuristics
-   **Search Box**: `input[name="q"]` or `id="searchboxinput"`.
-   **Feed Panel**: Identified via `role="feed"`. This is crucial for the scrolling logic.
-   **Scrolling**: The script executes JavaScript `element.scrollTop += X` to simulate a user scrolling. It waits for the scroll height to change to confirm new data loaded.

## ⚠️ Known Edge Cases
-   **"You've reached the end of the list"**: The scraper detects the text "You've reached the end" to abort early.
-   **No Results**: If Google Maps shows "No results found", the scraper captures a screenshot (`debug_no_results.png` during debug mode) and returns an empty list.
