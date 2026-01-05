import os
import sys

def test_env():
    print("="*60)
    print("   ENVIRONMENT TEST   ")
    print("="*60)
    
    # 1. Check Python
    print(f"Python Version: {sys.version.split()[0]}")
    
    # 2. Check Files
    required_files = ['credentials.json', 'input.txt', 'leads_scrapping.py', 'main.py']
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    print(f"Root Dir: {root_dir}")
    
    all_files_ok = True
    for f in required_files:
        path = os.path.join(root_dir, f)
        exists = os.path.exists(path)
        icon = "✅" if exists else "❌"
        print(f"{icon} {f}")
        if not exists:
            all_files_ok = False
            
    # 3. Check Imports
    print("\nChecking Libraries...")
    try:
        import gspread
        print("✅ gspread")
    except ImportError:
        print("❌ gspread missing")

    try:
        import playwright
        print("✅ playwright")
    except ImportError:
        print("❌ playwright missing")

    try:
        import pandas
        print("✅ pandas")
    except ImportError:
        print("❌ pandas missing")

    print("="*60)
    if all_files_ok:
        print("✅ Environment looks GOOD.")
    else:
        print("⚠️ Enable to find some files.")

if __name__ == "__main__":
    test_env()
