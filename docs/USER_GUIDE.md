# Google Maps Scraper Pro - User Guide

## 🚀 Quick Start

1.  **Download**: Get the `GoogleMapsScraper_v2.0.exe`.
2.  **Prepare**: Place your `input.txt` (queries) and `credentials.json` (Google Sheets access) in the same folder as the `.exe`.
3.  **Run**: Double-click `GoogleMapsScraper_v2.0.exe`.

---

## 🖥️ Interface Guide

### 1. General Tab
- **Input Queries File**: Browse to select your `input.txt`.
- **Credentials JSON**: Browse to select your `credentials.json`.
- **Headless Mode**: 
    - **ON** (Default): Browser runs invisibly in the background. Faster.
    - **OFF**: You see the browser window. Good for debugging.

### 2. Advanced Tab
- **Sheet Behavior**: Choose "Append" (add to existing) or "Overwrite".
- **Re-Install Browsers**: **IMPORTANT!** If the app says "Browsers not found", click this button. It will download the necessary Chrome files automatically.
- **Run Diagnostics**: Checks if Google Sheets connection is working.

### 3. Controls
- **START SCRAPING**: Begins the process.
- **PAUSE / RESUME**: Pauses immediately.
- **SKIP ITEM**: Skips the current city/keyword and moves to the next one in your list.
- **STOP**: Safely stops after finishing the current listing.

---

## 🛠️ Troubleshooting

### "No module named tkinter"
- This means the app was not built correctly. Contact the developer. 

### "Browsers not found"
- Go to **Advanced Tab** -> Click **Re-Install Browsers**.
- Wait for the popup to say "Success".

### App closes immediately
- Ensure `input.txt` exists and is not empty.
- Ensure `credentials.json` is valid.
