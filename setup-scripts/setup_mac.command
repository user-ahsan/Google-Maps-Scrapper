#!/bin/bash

# MacOS .command file to make setup clickable
# This script ensures we are in the correct directory and then runs the main setup script.

# Set the title for the terminal window
echo -n -e "\033]0;Google Maps Scraper - Mac Setup\007"

# Move to the directory where this script is located
cd "$(dirname "$0")"

echo "=========================================="
echo "   Google Maps Scraper - Mac Setup"
echo "=========================================="

# Ensure setup.sh is executable
if [ -f "setup.sh" ]; then
    chmod +x setup.sh
    ./setup.sh
else
    echo "Error: setup.sh not found!"
    echo "Please ensure you have extracted all files correctly."
fi

# Keep window open so user can read output
echo ""
echo "Process completed. You can close this window."
read -n 1 -s -r -p "Press any key to exit..."
