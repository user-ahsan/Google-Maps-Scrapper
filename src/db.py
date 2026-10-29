# Made by user-ahsan
import os
import re
import sqlite3

import pandas as pd

DB_PATH = os.path.join('GMaps Data', 'leads.db')

# Simple connection pool implementation
_connection_pool = []

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initialize the database:
    1. Create table if not exists.
    2. Check for missing columns and add them (Schema Migration).
    """
    conn = get_db_connection()
    try:
        # 1. Create Table with Core Schema
        # We use the keys that are always expected.
        # Note: We rely on text mainly, allowing flexibility.
        create_sql = '''
        CREATE TABLE IF NOT EXISTS leads (
            unique_key TEXT PRIMARY KEY,
            name TEXT,
            address TEXT,
            domain TEXT,
            website TEXT,
            phone_number TEXT,
            category TEXT,
            location TEXT,
            reviews_count INTEGER,
            reviews_average REAL,
            latitude REAL,
            longitude REAL,
            google_maps_link TEXT,
            scraped_query TEXT,
            scraped_at TEXT
        )
        '''
        conn.execute(create_sql)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_name ON leads(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_query ON leads(scraped_query)")

        # 2. Schema Migration: Check for missing columns
        # Get existing columns
        cursor = conn.execute("PRAGMA table_info(leads)")
        existing_cols = {row['name'] for row in cursor}

        # Define expected columns (Source of Truth)
        # This list should stay in sync with insert_business keys
        expected_cols = {
            'unique_key', 'name', 'address', 'domain', 'website',
            'phone_number', 'category', 'location', 'reviews_count',
            'reviews_average', 'latitude', 'longitude', 'google_maps_link',
            'scraped_query', 'scraped_at'
        }

        # Check and Add
        for col in expected_cols:
            if col not in existing_cols:
                print(f"   🛠️  DB Migration: Adding missing column '{col}'...")
                # SQLite only allows adding one column per ALTER statement
                # Default type TEXT is safest if we don't know, but we know some.
                col_type = "TEXT"
                if col in ['reviews_count']:
                    col_type = "INTEGER"
                if col in ['reviews_average', 'latitude', 'longitude']:
                    col_type = "REAL"

                try:
                    conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {col_type}")
                    print(f"   ✅ Added column {col}")
                except Exception as e:
                    print(f"   ❌ Failed to add column {col}: {e}")

        conn.commit()
    finally:
        close_connection(conn)

def close_connection(conn):
    """Safely closes a database connection."""
    try:
        conn.close()
    except Exception:
        pass

def get_known_names():
    """Returns a set of all normalized business names in the DB."""
    conn = get_db_connection()
    try:
        # Check if table exists first
        cursor = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='leads'")
        if cursor.fetchone()[0] == 0:
            return set()

        cursor = conn.execute("SELECT name FROM leads WHERE name IS NOT NULL")
        return {row['name'].strip().lower() for row in cursor}
    except Exception:
        return set()
    finally:
        close_connection(conn)

def get_existing_keys():
    """Returns a set of all unique keys in the DB."""
    conn = get_db_connection()
    try:
        # Check if table exists first
        cursor = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='leads'")
        if cursor.fetchone()[0] == 0:
            return set()

        cursor = conn.execute("SELECT unique_key FROM leads")
        return {row['unique_key'] for row in cursor}
    except Exception:
        return set()
    finally:
        close_connection(conn)

def insert_business(business_dict, unique_key):
    """
    Inserts a business into the database.
    Returns True if inserted, False if duplicate key.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # 1. Get current DB columns to avoid errors
        db_cols_cursor = conn.execute("PRAGMA table_info(leads)")
        db_cols = {row['name'] for row in db_cols_cursor}

        # 2. Prepare Data dict
        data = {'unique_key': unique_key}
        # Merge business_dict into data
        for k, v in business_dict.items():
            data[k] = v

        # 3. Check for new columns in the incoming data (sanitizing identifiers)
        cleaned_data = {}
        for key, val in data.items():
            safe_key = re.sub(r'[^a-zA-Z0-9_]', '', key)
            if safe_key and safe_key[0].isdigit():
                safe_key = '_' + safe_key
            if not safe_key:
                continue
            if safe_key not in db_cols:
                try:
                    print(f"     DB Schema Update: Found new field '{safe_key}'. Adding to table...")
                    conn.execute(f"ALTER TABLE leads ADD COLUMN {safe_key} TEXT")
                    db_cols.add(safe_key) # Mark as existing
                except Exception as e:
                    print(f"     Could not add column {safe_key}: {e}")
                    continue
            cleaned_data[safe_key] = val

        data = cleaned_data
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f'INSERT OR IGNORE INTO leads ({columns}) VALUES ({placeholders})'

        cur.execute(sql, list(data.values()))
        conn.commit()

        return cur.rowcount > 0
    finally:
        close_connection(conn)

def insert_businesses_batch(business_records):
    """
    Inserts multiple businesses in a single transaction with batch operations.
    business_records is a list of tuples: (business_dict, unique_key)
    Returns count of newly inserted records.
    """
    if not business_records:
        return 0

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # 1. Get current DB columns
        db_cols_cursor = conn.execute("PRAGMA table_info(leads)")
        db_cols = {row['name'] for row in db_cols_cursor}

        # 2. Check for missing columns across all incoming records
        all_safe_keys = set()
        for b_dict, _ in business_records:
            for k in b_dict.keys():
                safe_k = re.sub(r'[^a-zA-Z0-9_]', '', k)
                if safe_k and safe_k[0].isdigit():
                    safe_k = '_' + safe_k
                if safe_k:
                    all_safe_keys.add(safe_k)

        for safe_key in all_safe_keys:
            if safe_key not in db_cols:
                try:
                    conn.execute(f"ALTER TABLE leads ADD COLUMN {safe_key} TEXT")
                    db_cols.add(safe_key)
                except Exception:
                    pass

        # 3. Insert in single transaction
        cols_list = sorted(db_cols)
        columns_sql = ', '.join(cols_list)
        placeholders_sql = ', '.join(['?'] * len(cols_list))
        sql = f'INSERT OR IGNORE INTO leads ({columns_sql}) VALUES ({placeholders_sql})'

        rows_data = []
        for b_dict, unique_key in business_records:
            row_dict = {'unique_key': unique_key}
            for k, v in b_dict.items():
                safe_k = re.sub(r'[^a-zA-Z0-9_]', '', k)
                if safe_k and safe_k[0].isdigit():
                    safe_k = '_' + safe_k
                if safe_k:
                    row_dict[safe_k] = v
            row_vals = [row_dict.get(c) for c in cols_list]
            rows_data.append(row_vals)

        cur.executemany(sql, rows_data)
        conn.commit()
        return len(rows_data)
    except Exception as e:
        print(f"Batch DB insert error: {e}")
        return 0
    finally:
        close_connection(conn)

def import_csv_if_empty(csv_path):
    """One-time migration: Import CSV data if DB is empty."""
    if not os.path.exists(csv_path):
        return

    conn = get_db_connection()
    try:
        # Check emptiness
        count = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        if count > 0:
            return # Already has data

        print(f"   📦 Migrating {csv_path} to SQLite...")
        df = pd.read_csv(csv_path)

        # We need to map CSV columns to DB columns
        # Assuming CSV headers match our EXPECTED_HEADERS mostly
        # We'll use the sheets_utils.DEFAULT_MAPPING reversed or similar logic
        # For simplicity, we'll iterate and use generate_unique_key from sheets_utils (we need to inject it or import it)
        # Circular import risk? No, db doesn't import sheets_utils. Main will handle this or we duplicate logic.
        # Let's pass the logic in or simple loop.

        from src.sheets_utils import DEFAULT_MAPPING, generate_unique_key

        inserted_count = 0
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            # Normalize keys to lowercase internal names if possible, but CSV has Display Names
            # Map Display Name -> Internal Name
            internal_data = {}
            for internal, display in DEFAULT_MAPPING.items():
                if display in row_dict:
                    val = row_dict[display]
                    if pd.isna(val):
                        val = None
                    internal_data[internal] = val

            # Key generation (using row with Display Names is what generate_unique_key expects usually, check impl)
            # generate_unique_key uses .get('Name') etc. so row_dict works.
            key = generate_unique_key(row_dict)

            if insert_business(internal_data, key):
                inserted_count += 1

        print(f"   ✅ Migrated {inserted_count} records to leads.db")

    except Exception as e:
        print(f"   ❌ Migration failed: {e}")
    finally:
        conn.close()
