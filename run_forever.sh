#!/bin/bash

# Activate virtual environment just in case, though we use direct binary path below
source venv/bin/activate

echo "Starting Infinite Scraper Loop..."
echo "Press [CTRL+C] to stop."

while true; do
    echo "=========================================="
    echo "Starting scraper run at $(date)"
    echo "=========================================="
    
    # Run the scraper
    # Using the python binary inside the venv to ensure dependencies are loaded
    ./venv/bin/python main.py
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "Scraper crashed with exit code $EXIT_CODE. Restarting in 10 seconds..."
        sleep 10
    else
        echo "Scraper finished successfully. Restarting in 60 seconds..."
        sleep 60
    fi
done
