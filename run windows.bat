@echo off
SETLOCAL EnableDelayedExpansion
TITLE Google Maps Scraper - Universal Driver

:MENU
cls
echo ==========================================
echo    G-Maps Scraper Universal Driver
echo ==========================================
echo.
echo  [1] Run Scraper (Standard)
echo  [2] Run Scraper (Autonomous Mode - Default)
echo  [3] Fix/Re-install Environment
echo  [4] Exit
echo.
SET /P OPT="Select an option (1-4): "

IF "%OPT%"=="1" GOTO RUN_MANUAL
IF "%OPT%"=="2" GOTO RUN_AUTO
IF "%OPT%"=="3" GOTO FIX_ENV
IF "%OPT%"=="4" GOTO ERROR_EXIT
GOTO MENU

:FIX_ENV
echo.
echo [*] Removing old environment...
if exist "venv" (
    rmdir /s /q venv
)
echo [*] Creating new virtual environment...
python -m venv venv
IF %ERRORLEVEL% NEQ 0 (
    echo [X] Failed to create venv. Is Python installed?
    pause
    GOTO MENU
)
echo [*] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
echo [*] Environment Fixed!
pause
GOTO MENU

:CHECK_ENV
IF NOT EXIST "venv" (
    echo [!] Virtual environment not found. Creating it...
    GOTO FIX_ENV
)
EXIT /B 0

:RUN_MANUAL
CALL :CHECK_ENV
echo.
echo [*] Starting Scraper (Manual Mode)...
echo     (Press 'q' in Python window to quit if implemented, or Ctrl+C)
echo.
REM Using explicit path to avoid system python conflicts
.\venv\Scripts\python.exe main.py -m
GOTO FINISH

:RUN_AUTO
CALL :CHECK_ENV
echo.
echo [*] Starting Scraper (Autonomous Mode)...
echo.
echo.
SET /P SEARCH="Enter Search Query (or press 'n' to use input.txt): "
SET /P LIMIT="Enter Max Listings to Scroll (or press 'n' for No Limit): "

REM Logic for Search Argument
SET "ARG_S=-s "%SEARCH%""
IF /I "%SEARCH%"=="n" (
    SET "ARG_S="
    echo    [*] Using input.txt for queries...
)

REM Logic for Limit Argument
IF "%LIMIT%"=="" SET LIMIT=100
SET "ARG_T=-t %LIMIT%"
IF /I "%LIMIT%"=="n" (
    SET "ARG_T="
    echo    [*] No limit set. (Defaulting to Max)
) 

.\venv\Scripts\python.exe main.py %ARG_S% %ARG_T%
GOTO FINISH

:FINISH
echo.
echo ==========================================
echo    Scraping Finished.
echo ==========================================
echo.
SET /P RERUN="Run again? (Y/N): "
IF /I "%RERUN%"=="Y" GOTO MENU
EXIT /b 0

:ERROR_EXIT
EXIT /b 0
