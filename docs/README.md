# Google Maps Scraper Documentation 📚

Welcome to the comprehensive documentation for the Google Maps Scraper project.

## 🚀 For End Users
-   [**Setup Guide (Important)**](END_USER_SETUP.md): Getting `credentials.json` and first-run instructions.
-   [**User Guide**](USER_GUIDE.md): How to use the controls and features.
-   [**Maintenance**](MAINTENANCE.md): How to fix broken selectors.

## 🛠️ For Developers
-   [**Developer Guide**](DEVELOPER_GUIDE.md): High-level architecture and design concepts.
-   [**Setup Guide**](SETUP_GUIDE.md): How to install Python, Virtual Env, and dependencies.
-   [**Build Guide**](BUILD_GUIDE.md): How to compile the `.exe` using PyInstaller.
-   [**Project Structure**](PROJECT_STRUCTURE.md): A map of every file in the codebase.
-   [**Debugging Guide**](DEBUGGING_GUIDE.md): Solutions for common errors (Unicode, Headless, etc.).

## 🧪 Testing & Validation
-   [**Testing Summary**](TESTING_SUMMARY.md): How to run the automated test suite.
-   [**Test Details**](testing/): Detailed docs for each test file.

## 🧠 Code Deep Dive
Detailed technical documentation for core components:
-   [**Scraping Engine**](code/leads_scraping.md) (`src/leads_scraping.py`)
-   [**Data Handling**](code/sheets_utils.md) (`src/sheets_utils.py`)
-   [**Local Database**](code/db.md) (`src/db.py`)
-   [**GUI Architecture**](code/gui_architecture.md) (`gui_app.py`)
-   [**Entry Points**](code/entry_points.md) (`main.py`)
-   [**Configuration**](code/configuration.md) (`src/config_manager.py`)
-   [**Utilities**](code/utils.md) (`src/logger.py`, etc.)
-   [**Schema Migration**](code/schema_migration.md) (Dynamic Columns)
