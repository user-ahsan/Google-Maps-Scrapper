@echo off
:loop
echo ==========================================
echo Starting scraper run at %TIME%
echo ==========================================

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run installation steps first.
    pause
    exit /b
)

REM Activate venv and run
call venv\Scripts\activate.bat
python main.py

if %ERRORLEVEL% NEQ 0 (
    echo Scraper crashed or failed. Restarting in 10 seconds...
    timeout /t 10
) else (
    echo Scraper finished successfully. Restarting in 60 seconds...
    timeout /t 60
)
goto loop
