# How to Build the Google Maps Scraper Windows Executable

This guide explains how to compile the Google Maps Scraper into a standalone Windows executable (`.exe`) file using PyInstaller.

## 1. Prerequisites

Ensure you have the following set up before proceeding:
- **Python**: Installed on your system.
- **Virtual Environment**: The project's virtual environment should be set up.
- **Dependencies**: All required packages installed.

## 2. Environment Setup

1.  **Open a Terminal** (Command Prompt or PowerShell) in the project root directory (`d:\Projects\Google-Maps-Scrapper`).
2.  **Activate the Virtual Environment**:
    ```powershell
    .\venv\Scripts\activate
    ```
    *(You should see `(venv)` appear at the start of your command line.)*

3.  **Verify Dependencies**:
    Ensure all requirements are installed:
    ```powershell
    pip install -r requirements.txt
    ```

## 3. Building the Executable

The project includes a `scraper.spec` file that contains the build configuration (including hidden imports and asset collection).

To build the executable, run the following command found in the terminal:

```powershell
pyinstaller scraper.spec
```

This process may take a minute or two. You will see logs indicating the analysis and packaging process.

## 4. Locating the Output

Once the build completes successfully, your executable will be located in the `dist` folder:

*   **Path**: `dist\GoogleMapsScraper\GoogleMapsScraper.exe`

## 5. Running the Application

To run the application correctly, you must ensure the external configuration files are present in the same folder as the executable.

1.  **Navigate to the output folder**:
    ```powershell
    cd dist\GoogleMapsScraper
    ```

2.  **Prepare Configuration Files**:
    Copy the following files from your project root to this folder:
    *   `credentials.json` (Required for Google Sheets access)
    *   `input.txt` (Or any other input file you wish to select)

3.  **Run the App**:
    Double-click `GoogleMapsScraper.exe` or run it from the terminal:
    ```powershell
    .\GoogleMapsScraper.exe
    ```

## Troubleshooting

*   **Missing Modules**: If the app fails to start with "Module not found" errors, ensure the module is listed in `requirements.txt` and potentially added to the `hiddenimports` list in `scraper.spec`.
*   **Browser Issues**: The build script includes Playwright browsers. If you encounter browser errors, try running `playwright install chromium` in your environment and rebuilding, though the spec file attempts to collect them automatically.
*   **Console Output**: The current build is configured as a GUI application (`console=False`). If you need to see debug logs for startup errors, you can edit `scraper.spec` to set `console=True` and rebuild.
