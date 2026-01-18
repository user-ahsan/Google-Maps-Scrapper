# Entry Points (`main.py`)

## 📝 Overview
This file serves as the **Command Line Interface (CLI)** entry point. It orchestrates the setup, dependency checks, and execution of the scraping job when running in a server or headless environment.

## ⚙️ Workflow

### 1. Argument Parsing
Uses `argparse` to handle flags:
-   `-s "Search Query"`: Bypass interactive input.
-   `-headed`: Force the browser to show the UI (useful for debugging).
-   `-offline`: Skip Google Sheets connection checks.
-   `--install-browsers`: Internal flag used by the executable to trigger `playwright install`.

### 2. Diagnostics (`run_diagnostics`)
Before scraping starts, `main.py` runs a health check:
1.  **Browser**: Tries to launch a headless Chromium instance. If it fails, it attempts to self-repair by calling `playwright install`.
2.  **Database**: Calls `db.init_db()` to create tables and migrating schema.
3.  **Sheets**: Tries connecting to Google API using `credentials.json`.

### 3. Execution Loop
1.  Loads `known_names` from the local DB (fast deduplication).
2.  Fetches existing keys from Google Sheets (if online).
3.  Calls `leads_scraping.scrape_data(...)`.
4.  On completion:
    -   Saves results to SQLite (`save_to_db`).
    -   Exports results to CSV (`save_to_csv`).
    -   Uploads new rows to Google Sheets (if online).

## 🚀 Usage Example
```bash
# Run a specific search in headless mode
python main.py -s "Dentists in London" 

# Run vertically visible for debugging
python main.py -s "Pizza" -headed  
```
