# Master Debugging Guide

This guide compiles common errors and solutions for the Google Maps Scraper. It is designed to help new developers quickly resolve issues.

## 🚨 Critical Errors & Solutions

### 1. `UnicodeEncodeError: 'charmap' codec can't encode...`
**symptom**: The script crashes immediately when trying to print emoji-heavy logs on Windows.
**Fix**:
-   **Immediate**: The codebase now uses safe ASCII indicators (`[OK]`, `[PASS]`) instead of emojis for critical logs.
-   **Root Cause**: Windows Console (cmd/powershell) often defaults to legacy code pages (cp1252) instead of UTF-8.
-   **Verify**: Run `test/test_data_extraction.py`. If it passes, the safe logging is working.

### 2. `Playwright.ExecutableNotFoundError` or "Browser not found"
**Symptom**: "Could not find a usable browser instance".
**Fix**:
-   Run the internal installer: `python main.py --install-browsers`
-   Or manual install: `playwright install chromium`
-   **Verify**: Run `python test/test_browser.py`.

### 3. "No businesses scraped" (Headless Mode)
**Symptom**: Scraper runs but returns 0 results.
**Fix**:
-   **Check Layout**: Google Maps might have A/B tested a new design. Run `python test/test_headed_scrape.py` to watch the bot.
-   **Check Network**: Slow internet might cause timeouts finding the list. Increase `Wait` time in `config.json`.
-   **Check Selectors**: Look at `src/leads_scraping.py`. The `feed_selector` or search result XPaths might need updating.

### 4. Google Sheets "Insufficient Permission"
**Symptom**: `gspread.exceptions.APIError: 403`
**Fix**:
-   Open your Google Sheet in the browser.
-   Click **Share**.
-   Paste the `client_email` from your `credentials.json`.
-   **Verify**: Run `python test/test_sheets.py`.

### 5. `ModuleNotFoundError` in Executable
**Symptom**: The `.exe` crashes saying it can't find `fake_useragent` or `pandas`.
**Fix**:
-   This usually means a hook is missing in PyInstaller.
-   Check `scraper.spec`. Ensure `hiddenimports` includes the missing module.
-   Rebuild: `pyinstaller clean scraper.spec` -> `pyinstaller scraper.spec`.

## 🛠️ Debugging Workflow

1.  **Something is broken. Where do I start?**
    -   Run `python test/test_env.py`. Is your environment sane?
    -   Run `python test/test_config.py`. Is your config valid?

2.  **The Scraper crashes mid-run.**
    -   Check `debug.log`. (Ensure logging is enabled in `src/logger.py`).
    -   Is it a specific query? Try running just that query: `python main.py -s "problem query"`.

3.  **Data looks wrong (weird characters, duplicates).**
    -   Run `python test/test_data_extraction.py`. This checks the cleaning logic.
    -   Check `src/sheets_utils.py` -> `clean_text_for_csv`.

## 📱 Contact / Support
If you are stuck, refer to `docs/PROJECT_STRUCTURE.md` to find the exact file handling the broken feature.
