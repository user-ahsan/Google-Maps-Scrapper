#!/bin/bash

# setup.sh - Automated Environment Setup for Google Maps Scraper
# This script handles OS detection, cleaning old environments, creating a fresh venv, and installing dependencies.

set -e # Exit immediately if a command exits with a non-zero status.

echo "=========================================="
echo "   Google Maps Scraper - Auto Setup"
echo "=========================================="

# 0. Safety Check: Deactivate existing venv
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "[*] Detected active virtual environment ($VIRTUAL_ENV). Deactivating..."
    # We can't rely on 'deactivate' function being available in subshell/script
    # But we can strip it from PATH to be safe
    export PATH=$(echo $PATH | tr ":" "\n" | grep -v "$VIRTUAL_ENV" | tr "\n" ":")
    unset VIRTUAL_ENV
fi

# 1. OS Detection
OS="$(uname -s)"
case "${OS}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGW;;
    *)          machine="UNKNOWN:${OS}"
esac

echo "[*] Detected OS: ${machine}"

if [[ "$machine" == "Cygwin" || "$machine" == "MinGW" ]]; then
    echo "[!] Warning: It looks like you are running on Windows (via Git Bash/Cygwin)."
    echo "    This script is optimized for Linux/macOS. It may still work, but if it fails,"
    echo "    please try running the commands manually."
fi

# 2. Check for Python
# We explicitly want the SYSTEM python, not the one inside the venv we might delete.
if [ -f "/usr/bin/python3" ]; then
    PYTHON_CMD="/usr/bin/python3"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_CMD="/usr/local/bin/python3"
elif command -v python3 &>/dev/null; then
    # Fallback to whatever is in path, but check if it's our local venv
    CANDIDATE="$(command -v python3)"
    if [[ "$CANDIDATE" == *"$(pwd)/venv"* ]]; then
        echo "[!] Warning: 'python3' points to local venv. Trying to find system python..."
        # Try to find a python that isn't this one
        PYTHON_CMD=$(which -a python3 | grep -v "$(pwd)/venv" | head -n 1)
        if [ -z "$PYTHON_CMD" ]; then
             echo "[X] Error: Could not find system python3. Please deactivate venv and try again."
             exit 1
        fi
    else
        PYTHON_CMD="$CANDIDATE"
    fi
else
    echo "[X] Error: Python 3 could not be found. Please install Python 3.8+."
    exit 1
fi

echo "[*] Using Python binary: $PYTHON_CMD"
$PYTHON_CMD --version

# 3. Environment Health Check & Cleanup
HEAL_MODE=false

if [ -d "venv" ]; then
    echo "[?] Found existing 'venv'. Checking health..."
    # Try to activate and check python
    if ! source venv/bin/activate 2>/dev/null || ! python3 --version &>/dev/null; then
        echo "[!] Environment appears broken. Initiating self-healing..."
        HEAL_MODE=true
    else
        echo "[*] Existing environment seems valid."
        read -p "Do you want to force a full reinstall/repair? (y/N): " choice
        case "$choice" in 
          y|Y ) HEAL_MODE=true ;;
          * ) echo "[*] Keeping existing venv. Will update dependencies only.";;
        esac
    fi
else
    echo "[*] No environment found. Setting up fresh..."
    HEAL_MODE=true
fi

if [ "$HEAL_MODE" = true ]; then
    echo "[*] 🧹 Cleaning up old headers/files..."
    rm -rf venv
    
    echo "[*] 🔨 Creating fresh virtual environment..."
    $PYTHON_CMD -m venv venv
    
    # Validation
    if [ ! -f "venv/bin/python" ]; then
        echo "[X] CRITICAL ERROR: Failed to create virtual environment."
        echo "    Please check your python installation permissions."
        exit 1
    fi
fi

# 4. Activate and Install Dependencies
echo "[*] 📦 Syncing dependencies..."

# We use a subshell to activate venv so it doesn't affect the current shell state
(
    source venv/bin/activate
    
    # Upgrade pip to ensure smooth installation
    pip install --upgrade pip
    
    # Install requirements with error trapping
    if [ -f "requirements.txt" ]; then
        echo "[*] Installing Python libraries (this may take a moment)..."
        pip install -r requirements.txt || {
            echo "[X] Error installing requirements. Retrying with --no-cache-dir..."
            pip install --no-cache-dir -r requirements.txt
        }
    else
        echo "[!] Warning: requirements.txt not found. Skipping dependency installation."
    fi
    
    # Install Playwright browsers
    echo "[*] 🎭 Checking Playwright browsers..."
    playwright install chromium
) || {
    echo "[X] Setup failed during dependency installation."
    exit 1
}

# 5. Final Permissions
if [ -f "run_forever.sh" ]; then
    chmod +x run_forever.sh
fi
chmod +x setup.sh

echo "=========================================="
echo "   Setup Complete! 🚀"
echo "=========================================="
echo ""
echo "You can now run the scraper using:"
echo "   ./venv/bin/python leads_scrapping.py"
echo ""
echo "Or use the run forever script:"
echo "   ./run_forever.sh"
echo "=========================================="
