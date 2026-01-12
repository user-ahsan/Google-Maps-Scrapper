# Project Structure & Documentation

This folder contains documentation for the Google Maps Scraper GUI project.

## New Files
- **`gui_app.py`**: The main entry point for the GUI application. Uses `customtkinter` to render the window.
- **`main_gui_wrapper.py`**: A bridge script that allows `gui_app.py` to call the core scraper logic (`src/leads_scrapping.py`) while passing configuration and control signals (Pause/Stop).
- **`src/controller.py`**: Contains `ScraperController`, a thread-safe class used to signal "Pause", "Resume", or "Stop" events between the GUI thread and the scraper thread.
- **`scraper.spec`**: The configuration file for `PyInstaller`. It defines how to build the standalone `.exe`, including hidden imports and data files.

## Modified Files
- **`src/leads_scrapping.py`**: Refactored `scrape_data` function to accept a `controller` object. Added checks inside the scraping loop to pause execution or break early if stopped.
- **`requirements.txt`**: Added `customtkinter` and `pyinstaller`.

## How It Works
1. **Threaded Execution**: The GUI runs on the main thread. When you click "Start", it spawns a background thread running `main_gui_wrapper.run_gui_mode`.
2. **Log Redirection**: `sys.stdout` and `sys.stderr` are redirected to a queue, which the GUI polls to update the "Live Console" text box.
3. **Control Flow**:
   - **Pause**: The GUI calls `controller.pause()`. The scraper loop checks `controller.is_paused()` every iteration and blocks until resumed.
   - **Stop**: The GUI calls `controller.stop()`. The scraper loop breaks out of the iteration and saves whatever data it has collected so far.

## Troubleshooting

### PyInstaller & Tkinter Issues
If you see `ModuleNotFoundError: No module named 'tkinter'` when running the exe, it is because `PyInstaller` failed to find the Tcl/Tk libraries.

**The Fix:**
I have manually added the paths to the system Python's `DLLs` and `tcl` directories in `scraper.spec`:
```python
PYTHON_HOME = r"C:\Users\ahsan\AppData\Local\Programs\Python\Python313"
```
If you move this project to another machine, you **MUST** update `PYTHON_HOME` in `scraper.spec` or use `docs/setup_guide.md` for instructions.
