# Made by user-ahsan
import sqlite3
import os
import pandas as pd

DB_PATH = os.path.join('GMaps Data', 'leads.db')

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database table if it doesn't exist."""
    conn = get_db_connection()
    try:
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        
        # We store the unique key (Name|Phone etc) directly for fast dedupe
        # and also store all other fields.
        conn.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unique_key TEXT UNIQUE,
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
        ''')
        
        # Index for faster name lookups (deduplication optimization)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_name ON leads(name)')
        
        conn.commit()
    finally:
        conn.close()

def insert_business(business_dict, unique_key):
    """
    Inserts a business into the database.
    Returns True if inserted, False if duplicate key.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Prepare data
        data = {
            'unique_key': unique_key,
            'name': business_dict.get('name'),
            'address': business_dict.get('address'),
            'domain': business_dict.get('domain'),
            'website': business_dict.get('website'),
            'phone_number': business_dict.get('phone_number'),
            'category': business_dict.get('category'),
            'location': business_dict.get('location'),
            'reviews_count': business_dict.get('reviews_count'),
            'reviews_average': business_dict.get('reviews_average'),
            'latitude': business_dict.get('latitude'),
            'longitude': business_dict.get('longitude'),
            'google_maps_link': business_dict.get('google_maps_link'),
            'scraped_query': business_dict.get('scraped_query'),
            'scraped_at': business_dict.get('scraped_at')
        }
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f'INSERT OR IGNORE INTO leads ({columns}) VALUES ({placeholders})'
        
        cur.execute(sql, list(data.values()))
        conn.commit()
        
        return cur.rowcount > 0
    finally:
        conn.close()

def get_known_names():
    """Returns a set of all normalized business names in the DB."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT name FROM leads WHERE name IS NOT NULL")
        return {row['name'].strip().lower() for row in cursor}
    finally:
        conn.close()

def get_existing_keys():
    """Returns a set of all unique keys in the DB."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT unique_key FROM leads")
        return {row['unique_key'] for row in cursor}
    finally:
        conn.close()

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
        
        from src.sheets_utils import generate_unique_key, DEFAULT_MAPPING
        
        inserted_count = 0
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            # Normalize keys to lowercase internal names if possible, but CSV has Display Names
            # Map Display Name -> Internal Name
            internal_data = {}
            for internal, display in DEFAULT_MAPPING.items():
                if display in row_dict:
                    val = row_dict[display]
                    if pd.isna(val): val = None
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
