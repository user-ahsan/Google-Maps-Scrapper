# Test Headed Scrape Documentation
**File:** `test/test_headed_scrape.py`

## 🎯 Purpose
Similar to the Headless test, but runs with the **Browser Visible**. This is designed for **Visual Verification** by the developer. It is useful when the headless test is failing and you need to "see" why (e.g., is a Captcha appearing? Is the scroll getting stuck?).

## 🏃 How to Run
```powershell
python test/test_headed_scrape.py
```

## ⚠️ Notes
-   This test **steals focus**. Do not interact with your computer while it is running.
-   It waits 5 seconds at the end before closing so you can inspect the results visually.

## 🐞 Debugging
-   **Stuck on Search**: If the bot types but nothing happens, check if the "Search" button selector has changed.
-   **Scroll Not Working**: If the list doesn't grow, the mouse wheel emulation might need tweaking in `src/leads_scraping.py`.
