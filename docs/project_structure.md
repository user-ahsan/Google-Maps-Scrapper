# Project Codebase Documentation

This document serves as the request map for the codebase. Click the links below for detailed technical documentation on how each component works.

## 📚 Deep Dive Documentation

### 🧠 Core Logic
| Component | File | Documentation |
|-----------|------|---------------|
| **Scraping Engine** | `src/leads_scraping.py` | [View Logic Docs](code/leads_scraping.md) |
| **Data & Sheets** | `src/sheets_utils.py` | [View Logic Docs](code/sheets_utils.md) <br> [View Schema Docs](code/schema_migration.md) |
| **Local Database** | `src/db.py` | [View Logic Docs](code/db.md) <br> [View Schema Docs](code/schema_migration.md) |

### 🖥️ Interface & entry Points
| Component | File | Documentation |
|-----------|------|---------------|
| **CLI / Main** | `main.py` | [View Logic Docs](code/entry_points.md) |
| **GUI Architecture** | `gui_app.py` | [View Logic Docs](code/gui_architecture.md) |

### ⚙️ Infrastructure
| Component | File | Documentation |
|-----------|------|---------------|
| **Config & Security** | `src/config_manager.py` | [View Logic Docs](code/configuration.md) |
| **Utilities** | `src/logger.py` | [View Logic Docs](code/utils.md) |
| **Testing Suite** | `test/*.py` | [View Testing Docs](TESTING_SUMMARY.md) |

---

## 📂 Root Directory Files
| File | Description |
|------|-------------|
| **`run windows.bat`** | **Startup Script**. The recommended way to run the app on Windows. It creates/activates the virtual environment and installs dependencies before running `gui_app.py`. |
| **`scraper.spec`** | **Build Config**. The configuration file for PyInstaller. It defines how to bundle the python scripts, assets, and hidden imports into a single `.exe` file. |
| **`requirements.txt`** | **Dependencies**. Lists all the Python libraries (playwright, pandas, customtkinter, etc.) required to run the project. |
| **`config.json`** | **User Settings**. The persistent configuration file where users save their preferences (API keys, search limits, headless mode toggle). |
| **`credentials.json`** | **Secrets**. (Not in git) The Google Cloud Service Account key required for Google Sheets integration. |
