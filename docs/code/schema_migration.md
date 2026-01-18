# Schema Migration Documentation (`src/db.py`, `src/sheets_utils.py`)

## 📝 Overview
The system now includes robust **Dynamic Schema Migration**. This means the application can automatically adapt to new data fields without manual database wipes or crashes.

## 🔄 Local Database (`src/db.py`)
-   **Trigger**: `init_db()` called at startup in `main.py`.
-   **Logic**:
    1.  Inspects the `leads` table using `PRAGMA table_info`.
    2.  Compares existing columns with `EXPECTED_HEADERS`.
    3.  If a column is missing (e.g., you added `instagram_url` to the code), it executes:
        ```sql
        ALTER TABLE leads ADD COLUMN instagram_url TEXT
        ```
    4.  Logs the migration action to the console (`🛠️ DB Migration: Adding...`).

## ☁️ Google Sheets (`src/sheets_utils.py`)
-   **Trigger**: `map_columns_to_sheet()` called before `upload_data_to_sheet`.
-   **Logic**:
    1.  Reads the header row (Row 1) of the Google Sheet.
    2.  Compares against the DataFrame columns.
    3.  If new columns exist in the DataFrame but not the Sheet:
        -   Calculates the next available column index (e.g., Column `Z` -> `AA`).
        -   Updates the header row cells with the new column names.
    4.  This ensures new data isn't dropped or mismatched.

## 📂 CSV Files (`src/sheets_utils.py`)
-   **Trigger**: `save_to_csv()`.
-   **Logic**:
    -   When appending to an existing CSV, it checks if the new DataFrame has extra columns.
    -   It re-orders the DataFrame to match the CSV's schema + any new columns appended at the end.
    -   *Note*: Standard CSV writers handle adding columns automatically, but our logic ensures specific ordering (Expected fields first).
