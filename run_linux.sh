#!/bin/bash

# Google Maps Scraper - Universal Driver (Linux)

show_menu() {
    clear
    echo "=========================================="
    echo "   G-Maps Scraper Universal Driver (Linux)"
    echo "=========================================="
    echo ""
    echo "  [1] Run Scraper (Standard)"
    echo "  [2] Run Scraper (Autonomous Mode - Default)"
    echo "  [3] Fix/Re-install Environment"
    echo "  [4] Exit"
    echo ""
    read -p "Select an option (1-4): " OPT
}

check_env() {
    if [ ! -d "venv" ]; then
        echo "[!] Virtual environment not found. Creating it..."
        fix_env
    fi
}

fix_env() {
    echo ""
    echo "[*] Removing old environment..."
    rm -rf venv
    
    echo "[*] Creating new virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[X] Failed to create venv. Is 'python3-venv' installed?"
        read -p "Press Enter to continue..."
        return
    fi

    echo "[*] Installing dependencies..."
    source venv/bin/activate
    python3 -m pip install --upgrade pip
    pip install -r requirements.txt
    playwright install chromium
    echo "[*] Environment Fixed!"
    read -p "Press Enter to continue..."
}

run_manual() {
    check_env
    echo ""
    echo "[*] Starting Scraper (Manual Mode)..."
    echo "    (Press 'q' in Python window to quit if implemented, or Ctrl+C)"
    echo ""
    # Using explicit path
    ./venv/bin/python main.py -m
    finish_scrape
}

run_auto() {
    check_env
    echo ""
    echo "[*] Starting Scraper (Autonomous Mode)..."
    echo ""
    read -p "Enter Search Query (or press 'n' to use input.txt): " SEARCH
    read -p "Enter Max Listings to Scroll (or press 'n' for No Limit): " LIMIT

    ARG_S="-s \"$SEARCH\""
    if [ "$SEARCH" = "n" ]; then
        ARG_S=""
        echo "   [*] Using input.txt for queries..."
    fi

    if [ -z "$LIMIT" ]; then
        LIMIT=100
    fi
    ARG_T="-t $LIMIT"
    if [ "$LIMIT" = "n" ]; then
        ARG_T=""
        echo "   [*] No limit set. (Defaulting to Max)"
    fi

    echo "Running: ./venv/bin/python main.py $ARG_S $ARG_T"
    eval ./venv/bin/python main.py $ARG_S $ARG_T
    finish_scrape
}

finish_scrape() {
    echo ""
    echo "=========================================="
    echo "   Scraping Finished."
    echo "=========================================="
    echo ""
    read -p "Press any key to continue..."
}

# Main Loop
while true; do
    show_menu
    case $OPT in
        1) run_manual ;;
        2) run_auto ;;
        3) fix_env ;;
        4) exit 0 ;;
        *) echo "Invalid option." ;;
    esac
done
