# Test Scraper Basic Documentation
**File:** `test/test_scraper_basic.py`

## 🎯 Purpose
A middle-ground test between `test_browser` and `test_headed_scrape`. It navigates to Google Maps, types a query, and checks if **Search Results appear**. It *does not* extract data or save files. It strictly validates the **UI Interaction** (Input field selectors, Network loading).

## 🏃 How to Run
```powershell
python test/test_scraper_basic.py
```

## 🐞 Debugging Use Case
-   If this test fails (timeouts matching selectors), it means Google Maps has updated its **CSS Classes** or **DOM Structure**. You likely need to update `src/selector_db.json` or `leads_scraping.py`.
