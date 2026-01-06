# Google Maps Scraper (Professional Edition)

A robust, enterprise-grade Python tool for scraping business data from Google Maps. It supports **offline csv storage**, **Google Sheets integration**, real-time deduplication, and intelligent error handling.

## 🚀 Features

-   **Dual Mode Storage**:
    -   **Cloud**: Automatically syncs data to Google Sheets ("Gmaps Leads").
    -   **Offline**: Saves data locally to `GMaps Data/` CSVs if no internet or credentials are found.
-   **Smart Deduplication**: Checks against existing records (locally and online) to prevent duplicate entries before clicking.
-   **Optimization**: Pre-loads known business names to skip redundant clicks, significantly speeding up large scrapes.
-   **Standardized Extraction**: Captures Name, Phone, Address, Website, **Business Status** (Open/Closed), **Review Count**, **Average Rating**, and Coordinates.
-   **Resilient**:
    -   Handles network timeouts and loading states.
    -   Standardized User-Agent to ensure consistent data extraction (fixes missing review counts).
    -   **Interactive Skip**: Press `s` during the scrolling phase to skip waiting if no new results appear.
-   **Bulk Search**: Reads multiple queries from `input.txt` or via command line argument.

---

## 📋 Prerequisites

-   **Python 3.8+**
-   **Google Cloud Service Account** (Optional, for Sheets Sync):
    -   `credentials.json` file in the root directory.
    -   A Google Sheet named "Gmaps Leads" (or similar) shared with the service account email.

---

## 🛠️ Installation & Setup (Copy-Paste Ready)

### 🪟 Windows Setup

**Option 1: Automated (Easiest)**
Double-click `setup.bat` in the folder.

**Option 2: Manual (Command Prompt)**
Copy and paste these commands one by one:
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 🍎 Mac / 🐧 Linux Setup

**Option 1: Automated**
```bash
chmod +x setup.sh
./setup.sh
```

**Option 2: Manual (Terminal)**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

---

## 🏃 Usage Commands

The entry point is `main.py`. Ensure your virtual environment is active before running these.

### 🪟 Windows Commands

**1. Run Standard Scraper (Reads input.txt)**
```cmd
venv\Scripts\python main.py
```

**2. Single Query Search**
```cmd
venv\Scripts\python main.py -s "gyms in New York"
```

**3. Run with Browser Visible (Headed Mode)**
*Use this if you want to see what the bot is doing.*
```cmd
venv\Scripts\python main.py -s "coffee shops" -t 10 -headed
```

### 🍎 Mac / 🐧 Linux Commands

**1. Run Standard Scraper (Reads input.txt)**
```bash
./venv/bin/python3 main.py
```

**2. Single Query Search**
```bash
./venv/bin/python3 main.py -s "gyms in New York"
```

**3. Run with Browser Visible**
```bash
./venv/bin/python3 main.py -s "coffee shops" -t 10 -headed
```

**Arguments:**
- `-s`, `--search`: Search query string (overrides input.txt).
- `-t`, `--total`: Limit number of results to scrape per query (default: 1,000,000).
- `-headed`: Run browser in visible mode (default is headless/invisible).
- `-y`, `--yes`: Auto-accept prompts (useful for automation).

---

## 🔧 Troubleshooting & Diagnostics

If you encounter issues, use the included test scripts to diagnose the problem.

### 1. Check Environment & Configuration
*Verifies Python version, libraries, and presence of `credentials.json` / `input.txt`.*

**Windows**:
```cmd
venv\Scripts\python test/test_env.py
```
**Mac/Linux**:
```bash
./venv/bin/python3 test/test_env.py
```

### 2. Test Browser Launch
*Launches a visible browser window and visits Google. If this fails, Playwright is not installed correctly.*

**Windows**:
```cmd
venv\Scripts\python test/test_browser.py
```
**Mac/Linux**:
```bash
./venv/bin/python3 test/test_browser.py
```

### 3. Test Google Sheets Connection
*Attempts to write a test value to your Sheet and delete it. Verifies your `credentials.json` and Sheet permissions.*

**Windows**:
```cmd
venv\Scripts\python test/test_sheets.py
```
**Mac/Linux**:
```bash
./venv/bin/python3 test/test_sheets.py
```

### 4. Test Basic Scraping Logic
*Runs a mini-scrape without saving data, just to check if Google Maps selectors have changed.*

**Windows**:
```cmd
venv\Scripts\python test/test_scraper_basic.py
```
**Mac/Linux**:
```bash
./venv/bin/python3 test/test_scraper_basic.py
```

### Common Issues

**Q: Review counts are missing?**
A: This version uses a fixed Desktop User-Agent to ensure Google serves the full desktop site. If they are still missing, run the scraper with `-headed` to see if Google is serving a mobile view or blocking the request.

**Q: "SpreadsheetNotFound" Error**
A: Ensure you have shared your Google Sheet with the `client_email` found in `credentials.json`. The script looks for a sheet named "Gmaps Leads" by default.

**Q: Script freezes while scrolling?**
A: Press `s` in the terminal to force the script to skip the wait and proceed to scraping the current list.