# Local Database Logic (`src/db.py`)

## 📝 Overview
Manages the local **SQLite 3** database (`GMaps Data/leads.db`). This provides a faster, more robust alternative to CSVs for storing millions of records and performing quick existence checks.

## ⚙️ Key Functions

### `init_db()`
**Run at Startup**.
1.  Connects to `leads.db`.
2.  Creates the `leads` table if it doesn't exist.
3.  **Schema Migration**: Checks existing columns in the table against the current code definition.
4.  **Alter Table**: If a new field (e.g., `scraped_at`) is missing from the DB, it executes `ALTER TABLE leads ADD COLUMN ...` to sync the schema automatically.

### `insert_business(business_dict, unique_key)`
-   **Atomic Insert**: logic uses `INSERT OR IGNORE` based on the `unique_key`.
-   **Dyanmic Fields**: Inspects the incoming dictionary. If the dictionary has keys that don't exist as columns, it adds them on-the-fly (though `init_db` usually handles this).

### `get_known_names_cached()`
-   **Performance**: Fetches *only* the `name` column for all records.
-   **Purpose**: Loads into a Python `set` for O(1) lookup times during scraping, preventing the scraper from clicking on businesses we've already scraped.

## 📂 Database Schema
The table `leads` typically contains:
-   `unique_key` (Primary Key, TEXT)
-   `name`
-   `phone_number`
-   `address`
-   `website`
-   `...` (and any dynamically added columns)
