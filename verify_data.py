import pandas as pd
import os

csv_path = 'GMaps Data/Gmaps Leads.csv'

if not os.path.exists(csv_path):
    print(f"❌ File not found: {csv_path}")
else:
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Loaded {len(df)} rows.")
        
        # Check last 3 rows specifically
        print("\n🔍 Last 3 Scraped Entries:")
        cols = ['Name', 'Phone Number', 'Reviews Average', 'Reviews Count']
        print(df[cols].tail(3).to_markdown(index=False))
        
        # Check for empty important fields in the whole dataset
        empty_names = df['Name'].isna().sum() 
        empty_phones = df['Phone Number'].isna().sum()
        print(f"\n📊 Stats:\n- Missing Names: {empty_names}\n- Missing Phones: {empty_phones}")
        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
