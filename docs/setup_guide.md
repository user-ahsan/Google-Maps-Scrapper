# Developer Setup & Build Guide

This guide details how to consistently set up the environment and build the Google Maps Scraper executable on Windows and Linux.

> [!IMPORTANT]
> **Why this guide uses explicit paths:**
> Many systems have multiple Python versions. To avoid errors like `ModuleNotFoundError` even after installing packages, we explicitly use the `python` executable inside our virtual environment (venv) instead of the system-wide command.

## 1. Prerequisites

- **Python 3.10+**: Ensure Python is installed.
- **Git**: For version control.

## 2. Setting Up the Virtual Environment

Isolate dependencies to prevent conflicts.

### Windows (Command Prompt / PowerShell)

1.  **Create Venv**:
    ```powershell
    python -m venv venv
    ```
2.  **Activate & Install**:
    ```powershell
    .\venv\Scripts\python.exe -m pip install -r requirements.txt
    ```
    *Note: We invoke python directly from the Scripts folder to be safe.*

3.  **Install Playwright Browsers**:
    ```powershell
    .\venv\Scripts\python.exe -m playwright install chromium
    ```

### Ubuntu / Linux / macOS

1.  **Create Venv**:
    ```bash
    python3 -m venv venv
    ```
2.  **Activate & Install**:
    ```bash
    ./venv/bin/python -m pip install -r requirements.txt
    ```
3.  **Install Browsers**:
    ```bash
    ./venv/bin/python -m playwright install chromium
    ```

## 3. Running the Application (Development)

To test the GUI before building:

**Windows:**
```powershell
.\venv\Scripts\python.exe gui_app.py
```

**Linux/macOS:**
```bash
./venv/bin/python gui_app.py
```

## 4. Building the Executable

We use **PyInstaller** with a custom configuration file (`scraper.spec`).

### Build Command

**Windows:**
```powershell
python -m PyInstaller scraper.spec --clean --noconfirm
```

### Build output
The result is a single file: `dist/GoogleMapsScraper.exe`.

## 5. Troubleshooting Common Issues

### "No module named tkinter"
The `scraper.spec` has been patched to manually include Tcl/Tk DLLs from `C:\Users\ahsan\AppData\Local\Programs\Python\Python313`. 
**If you are not Ahsan**, you must edit `scraper.spec` and update `PYTHON_HOME` to match your Python 3.13 installation path.

### "Playwright browsers not found"
1. Run the App.
2. Go to **Advanced Tab**.
3. Click **Re-Install Browsers**.
