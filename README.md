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

## 🛠️ Installation & Setup

### 1. Automated Setup (Recommended)
**Windows**:
Double-click `setup.bat` or run:
```cmd
setup.bat
```

**Mac/Linux**:
```bash
chmod +x setup.sh
./setup.sh
```

### 2. Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

---

## 🏃 Usage

The entry point is `main.py`.

### 1. Basic Run (Reads from input.txt)
1. Add queries to `input.txt` (one per line).
2. Run:
   ```bash
   venv\Scripts\python main.py
   ```

### 2. Single Query via Command Line
```bash
venv\Scripts\python main.py -s "gyms in London"
```

### 3. Limited Run (Headed Mode)
Great for debugging or watching the process.
```bash
venv\Scripts\python main.py -s "coffee shops" -t 10 -headed
```

**Arguments:**
- `-s`, `--search`: Search query string.
- `-t`, `--total`: Limit number of results to scrape per query.
- `-headed`, `--headed`: Run browser in visible mode (default is headless).
- `-y`, `--yes`: Auto-accept prompts (useful for automation).

---

## 🧪 Verification
Run the improved diagnostics included in the main script, or use specific test tools:

- `venv\Scripts\python test/test_env.py`: Check environment.
- `venv\Scripts\python test/test_sheets.py`: Check Google Sheets write permissions.

---

## 📂 Data Output

-   **Local**: `GMaps Data/Gmaps Leads.csv` (Primary source of truth for offline mode).
-   **Cloud**: Appended to "Gmaps Leads" spreadsheet (Worksheet: "Data 1" or first available).

## ❓ Troubleshooting

**Q: Review counts are missing?**
A: This version uses a fixed Desktop User-Agent to ensure Google serves the full desktop site, which includes review counts. Ensure you are running the latest code.

**Q: "SpreadsheetNotFound" Error**
A: Ensure you have shared your Google Sheet with the `client_email` found in `credentials.json`. The script looks for a sheet named "Gmaps Leads" by default.