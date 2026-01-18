# Test Browser Documentation
**File:** `test/test_browser.py`

## 🎯 Purpose
A minimalist check to see if **Playwright** can actually launch the Chrome binary and render a page. It removes the complexity of the Google Maps UI and just opens `google.com` and `example.com`.

## When to use
Use this if `test_headless_scrape.py` is crashing immediately with vague errors. This confirms if the issue is with the *Scraper Logic* (selectors) or the *Browser Engine* (installation).

## 🏃 How to Run
```powershell
python test/test_browser.py
```
