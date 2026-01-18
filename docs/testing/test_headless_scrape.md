# Test Headless Scrape Documentation
**File:** `test/test_headless_scrape.py`

## 🎯 Purpose
This is the **Gold Standard** end-to-end integration test. It simulates a real scraping run using a **Headless Browser** (invisible window). It verifies that the entire pipeline works: launching browser -> searching -> scraping leads -> saving data.

## ⚙️ Test Configuration
-   **Query**: "Coffee shops in New York" (default)
-   **Limit**: 5 leads (hardcoded limit to keep test fast)
-   **Mode**: Headless (no UI visible)

## 🏃 How to Run
```powershell
python test/test_headless_scrape.py
```

## ✅ Expected Output
```text
   HEADLESS SCRAPING TEST (5 results)
1. Launching Browser (Headless)...
2. Navigate to Google Maps...
3. Running scrape for: Coffee shops in New York
...
   [OK] Sponsored | ...
   [OK] ...
...
[PASS] HEADLESS SCRAPE TEST PASSED
```

## 🐞 Common Failures & Debugging
-   **Timeout Finding Search Box**: The test fails if it can't find `input[name="q"]`. This usually means Google Maps changed their layout (rare) or the network is very slow.
-   **"No businesses scraped"**: checking `headless_debug_output.txt` (if generated) or the console logs.
    -   *Cause 1*: IP Ban / Captcha.
    -   *Cause 2*: Search query returned no results.
-   **NoneType Error**: If you see `'NoneType' object has no attribute 'business_list'`, it implies `scrape_data` crashed or returned nothing (fixed in v2.1).
-   **Screenshots**: On failure, the test attempts to save `headless_failure.png`. Check this image to see what the browser saw at the moment of failure.
