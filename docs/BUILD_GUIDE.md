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
pyinstaller scraper.spec --clean --noconfirm
```

- **Output**: The executable will be in `dist\GoogleMapsScraper\GoogleMapsScraper.exe`.
- **Note**: The `scraper.spec` file is configured to bundle `credentials.json` logic, but you might need to copy your actual `credentials.json` next to the `.exe` if the app requests it at runtime.

### Ubuntu Build
PyInstaller builds **native** binaries. You cannot build a Windows `.exe` on Linux easily. This command will create a Linux executable.

```bash
pyinstaller scraper.spec --clean --noconfirm
```

- **Output**: The executable will be in `dist/GoogleMapsScraper/GoogleMapsScraper`.
- **Running**: You may need to mark it executable: `chmod +x dist/GoogleMapsScraper/GoogleMapsScraper`.

---

## 5. Debugging & Common Issues

### "No module named 'tkinter'" (Windows)
This happens if PyInstaller cannot find the Tcl/Tk DLLs in your Python installation.
**Fix**:
1. Open `scraper.spec`.
2. Locate the `MANUAL FIX` section.
3. Ensure `PYTHON_HOME` points to your actual system Python installation (e.g., `C:\Users\YourName\AppData\Local\Programs\Python\Python313`).
4. Re-run the build command.

### "Browser executables not found"
If the app fails to launch the browser:
- Ensure you ran `playwright install chromium` in the environment where you built the exe.
- The `scraper.spec` attempts to collect Playwright binaries, but sometimes strict antivirus policies block them.

### "Permission Denied" during Build
If `pyinstaller` fails with "Access is denied" or "PermissionError":
1. Close any running instances of the app.
2. Manually delete the `dist` and `build` folders.
   - Powershell: `Remove-Item -Recurse -Force dist, build`
3. Try building again.

### Console Window
By default, the `scraper.spec` has `console=False` for a cleaner GUI experience.
- To see startup errors (if the GUI doesn't appear), edit `scraper.spec`:
  Change `console=False` to `console=True`.
- Rebuild and run. You will now see a terminal window alongside the app with error logs.
