@echo off
SETLOCAL EnableDelayedExpansion

TITLE Google Maps Scraper - Auto Setup

echo ==========================================
echo    Google Maps Scraper - Auto Setup
echo ==========================================

:: 1. Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [X] Error: Python is not installed or not in your PATH.
    echo     Please install Python 3.8+ from python.org and tick "Add to PATH".
    pause
    exit /b 1
)

echo [*] Python found.

:: 2. Cleanup Old Environment
IF EXIST "venv" (
    echo [?] Found existing 'venv'. Check health?
    SET /P REPAIR="Do you want to force a repair/reinstall? (Y/N): "
    IF /I "!REPAIR!"=="Y" (
        echo [*] Cleaning up old environment...
        rmdir /s /q venv
        echo [*] Done.
    ) ELSE (
        echo [*] Keeping existing environment. Use 'Y' next time if you have issues.
    )
)

:: 3. Create Virtual Environment
IF NOT EXIST "venv" (
    echo [*] Creating new virtual environment...
    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        echo [X] Failed to create venv.
        pause
        exit /b 1
    )
)

:: 4. Activate and Install Dependencies
echo [*] Activating venv and installing dependencies...
call venv\Scripts\activate.bat

echo [*] Upgrading pip...
python -m pip install --upgrade pip

IF EXIST "requirements.txt" (
    echo [*] Installing requirements...
    pip install -r requirements.txt
) ELSE (
    echo [!] requirements.txt not found.
)

echo [*] Checking Playwright browsers...
playwright install chromium

echo ==========================================
echo    Setup Complete!
echo ==========================================
echo.
echo You can now run the scraper using:
echo    venv\Scripts\python leads_scrapping.py
echo.
echo Or simply run 'run_forever.bat' if available.
echo.
pause
