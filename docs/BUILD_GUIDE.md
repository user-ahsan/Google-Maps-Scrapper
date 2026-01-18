# Build & Setup Guide

This guide covers how to set up the development environment, install dependencies, and build the standalone executable for the Google Maps Scraper GUI.

## 1. Prerequisites
- **Python 3.10+** installed on your system.
- **Git** (optional, for cloning).

---

## 2. Setting Up Virtual Environment

It is highly recommended to use a virtual environment (venv) to keep dependencies isolated.

### Windows
1. Open PowerShell or Command Prompt.
2. Navigate to the project directory.
3. Run:
   ```powershell
   python -m venv venv
   ```
4. Activate the environment:
   ```powershell
   .\venv\Scripts\activate
   ```
   *(You should see `(venv)` appear at the start of your command line)*

### Ubuntu / Linux
1. Open Terminal.
2. Navigate to the project directory.
3. Run:
   ```bash
   python3 -m venv venv
   ```
4. Activate the environment:
   ```bash
   source venv/bin/activate
   ```

---

## 3. Installing Dependencies

Once the venv is active:

1. **Install Python Libraries**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright Browsers**:
   ```bash
   playwright install chromium
   ```

3. **System Dependencies (Ubuntu Only)**:
   If you are on Linux, you likely need to install Tkinter system libraries manually:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-tk
   ```

---

## 4. Building the Executable

We use **PyInstaller** to create the standalone application.

### Windows Build
Run the following command in your terminal (with venv active):

```powershell
python -m PyInstaller scraper.spec --clean --noconfirm
```

- **Output**: The executable will be `dist\GoogleMapsScraper_v2.0.exe`.
- **Note**: Copy `credentials.json` to the same folder as the `.exe` before running.

### Ubuntu Build
PyInstaller builds **native** binaries. You cannot build a Windows `.exe` on Linux easily.

## 5. Debugging & Common Issues

### "No module named 'tkinter'"
**Critical Fix in `scraper.spec`**:
The spec file hardcodes `PYTHON_HOME` to find Tcl/Tk DLLs.
1. Open `scraper.spec`.
2. Update line `PYTHON_HOME = r"..."` to point to your Python install folder.
3. Re-run the build command.

### "Browser executables not found"
Use the in-app **"Re-Install Browsers"** button in the Advanced Tab. This uses the bundled logic to download them locally.
