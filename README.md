# Google Maps Scraper Pro 🌍

An advanced, robust, and user-friendly tool to scrape business leads from Google Maps. Features a modern GUI, automatic deduplication, Google Sheets integration, and SQLite caching.

## 📚 Documentation Index

### 🚀 Getting Started
-   [**End User Setup Guide**](docs/END_USER_SETUP.md): **Start Here**. Instructions on getting your `credentials.json` and running the app.
-   [**User Manual**](docs/USER_GUIDE.md): How to use the interface, search modes, and features.

### 🛠️ Maintenance & troubleshooting
-   [**Maintenance Guide**](docs/MAINTENANCE.md): How to update CSS selectors if Google Maps changes.
-   [**Debugging Guide**](docs/DEBUGGING_GUIDE.md): Solutions for common errors/crashes.

### 💻 For Developers
-   [**Developer Overview**](docs/DEVELOPER_GUIDE.md): Architecture and design patterns.
-   [**Setup & Build**](docs/SETUP_GUIDE.md): How to install Python env and build the `.exe`.
-   [**Project Structure**](docs/PROJECT_STRUCTURE.md): File-by-file codebase map.
-   [**Code Deep Dive**](docs/code/): Technical implementation details.

---

## ✨ Key Features
-   **Anti-Detection**: Uses `fake-useragent` and human-like scrolling.
-   **Robustness**: Headless mode support, auto-recovery from network errors.
-   **Data Integrity**: 
    -   Automatic Deduplication (checks both local DB and Google Sheet).
    -   Dynamic Schema (automatically adds new columns if found).
-   **Output Formats**:
    -   CSV (`GMaps Data/`)
    -   SQLite Database (`GMaps Data/leads.db`)
    -   Google Sheets (Real-time sync)

## 📦 Installation (Source)
```bash
# 1. Clone repo
git clone https://github.com/your-repo/Google-Maps-Scrapper.git
cd Google-Maps-Scrapper

# 2. Setup Env
python -m venv venv
.\venv\Scripts\activate

# 3. Install Dependencies
pip install -r requirements.txt
playwright install chromium

# 4. Run
python main.py -headed
# OR
python gui_app.py
```

## 🏗️ Build (Executable)
```powershell
python -m PyInstaller scraper.spec --clean --noconfirm
```
executable will be in `dist/GoogleMapsScraper_v2.0.exe`.