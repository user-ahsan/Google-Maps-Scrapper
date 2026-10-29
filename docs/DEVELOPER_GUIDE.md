# Developer Guide

## Architecture Overview

The application is a hybrid **Python GUI (CustomTkinter)** wrapping a **Playwright-based Scraper**.

### Core Components

1.  **GUI (`gui_app.py`)**:
    - **Main Thread**: Renders UI, handles inputs.
    - **Background Thread**: Runs the scraping logic to keep UI responsive.
    - **Controller**: Uses `src/controller.py` to communicate (Pause/Resume/Stop/Skip) with the scraper thread.
    - **Console**: Redirects `stdout` to a text box using a queue.

2.  **Scraper Logic (`src/leads_scraping.py` & `main_gui_wrapper.py`)**:
    - **Wrapper**: Bridges the GUI args to the scraper function.
    - **Scraping Loop**: Run inside `scrape_data`. It checks `controller.is_paused()` and `controller.is_skipped()` inside the scrolling loop.

3.  **Build System (`scraper.spec`)**:
    - Uses **PyInstaller**.
    - **Critical**: Manually bundles Tcl/Tk DLLs because auto-detection often fails in virtual environments.
    - **OneFile**: Packages everything into a single `.exe`.

---

## Build Process

### 1. The Spec File (`scraper.spec`)
The spec file is customized to:
- Collect `customtkinter` assets.
- Collect `fake_useragent` data.
- **Force Include** `tcl86t.dll` and `tk86t.dll` from the developer's machine paths (Defined in `PYTHON_HOME` variable inside the spec).

> [!WARNING]  
> If you change your Python version or moves project to a new PC, you **MUST** update the `PYTHON_HOME` path in `scraper.spec`.

### 2. Building
Run this command in the virtual environment:
```powershell
python -m PyInstaller scraper.spec --clean --noconfirm
```

### 3. Browser Installation Handling
The frozen exe cannot run `python -m playwright install`.
- **Solution**: `gui_app.py` detects the `--install-browsers` flag. 
- When you click "Install Browsers", the app spawns a subprocess: `[current_exe] --install-browsers`.
- The main block detects this flag and calls `playwright.main.main(['install', 'chromium'])` internal API.

---

## Key Files
- `src/controller.py`: Thread synchronization primitives.
- `scraper.spec`: Build configuration.
- `gui_app.py`: UI and Process Management.

For detailed technical documentation on each file, see:
-   [**Entry Points**](code/entry_points.md)
-   [**Scraping Engine**](code/leads_scraping.md)
-   [**Data Handling**](code/sheets_utils.md)
-   [**Database**](code/db.md)
-   [**GUI Architecture**](code/gui_architecture.md)

