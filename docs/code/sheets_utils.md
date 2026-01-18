# Sheets & Data Utilities (`src/sheets_utils.py`)

## 📝 Overview
This module acts as the **Data Abstraction Layer**. It handles all data persistence (Saving to Disk) and synchronization (Google Sheets API). It also enforces data schema and cleanliness.

## ⚙️ Key Components

### `clean_text_for_csv(text)`
Prepares strings for storage.
-   Removes newlines and tabs to prevent CSV breakage.
-   Collapses multiple spaces into one.
-   **Usage**: Applied to every field before creating the `Business` object.

### `generate_unique_key(row_data)`
The logic for Deduplication.
-   **Formula**: `Name | Phone` (Primary) OR `Name | Address` (Secondary).
-   **Why?**: Google Maps often lists the same business slightly differently. This key ensures we don't save duplicates even across different runs.

### `save_to_csv(filename)`
-   **Locking**: Uses `msvcrt` (Windows) or `fcntl` (Linux) to strictly lock the file. This prevents corruption if you run multiple instances of the scraper simultaneously.
-   **Encoding**: Uses `utf-8-sig` for full Excel compatibility (including Emojis).
-   **Dynamic Schema**: Automatically adds new columns to the header if the internal logic changes.

### `upload_data_to_sheet(worksheet, df)`
Interacts with the Google Sheets API via `gspread`.
-   **Batch Upload**: Converts valid rows to a list of lists and appends them in one API call for performance.
-   **Schema Migration**: Checks the Sheet's header row. If the code has new fields (e.g., "Instagram"), it **dynamically appends** that column to the Sheet before uploading data.

## 🔄 Dynamic Schema Migration
This file contains logic to compare existing headers (in CSV or Google Sheet) with the current code's `EXPECTED_HEADERS`.
-   If `Code Headers != File Headers`, it calculates the difference.
-   It appends the missing columns to the right side of the existing file/sheet.
-   It ensures no data is lost during code updates.
