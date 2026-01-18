# Testing Guide for Google Maps Scraper

This directory contains documentation for the automated test suite. These tests ensure the reliability of the configuration, environment, data extraction logic, and scraper functionality.

## 📂 Test Files Overview

| Test File | Purpose | Documentation |
|-----------|---------|---------------|
| `test_env.py` | Validates Python environment, dependencies, and file structure. | [View Guide](testing/test_env.md) |
| `test_config.py` | Verifies `config.json` parsing, validation, and defaults. | [View Guide](testing/test_config.md) |
| `test_data_extraction.py` | Tests pure functions for text cleaning, emoji removal, and phone validation. | [View Guide](testing/test_data_extraction.md) |
| `test_browser.py` | Simple checks for Playwright browser launch and navigation. | [View Guide](testing/test_browser.md) |
| `test_sheets.py` | specialized test for Google Sheets API connectivity (Read/Write). | [View Guide](testing/test_sheets.md) |
| `test_scraper_basic.py` | Tests basic UI interactions (search input, scroll) without full scraping logic. | [View Guide](testing/test_scraper_basic.md) |
| `test_headed_scrape.py` | Full end-to-end scrape test with **visible** browser. | [View Guide](testing/test_headed_scrape.md) |
| `test_headless_scrape.py` | Full end-to-end scrape test in **headless** mode (CI/Background friendly). | [View Guide](testing/test_headless_scrape.md) |

## 🚀 Quick Start

To run all data logic tests (fast):
```powershell
python -m pytest test/test_data_extraction.py
python -m pytest test/test_config.py
```

To run a full scraper functionality check:
```powershell
python test/test_headless_scrape.py
```

## 🛠️ Debugging Tips

1. **Unicode Issues**: If you see `UnicodeEncodeError`, ensure your console supports UTF-8, or rely on the test logs which now use safe ASCII indicators (`[PASS]`, `[FAIL]`).
2. **Timeouts**: If scraper tests fail with timeouts, check your internet connection or increase `timeout` values in the test files.
3. **Missing Files**: Run `test_env.py` first to confirm `credentials.json` and other required files exist.
