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
        icon = "[OK]" if exists else "[FAIL]"
        print(f"{icon} {f}")
        if not exists:
            all_files_ok = False
            
    # 3. Check Imports
    print("\nChecking Libraries...")
    try:
        import gspread
        print("[OK] gspread")
    except ImportError:
        print("[FAIL] gspread missing")

    try:
        import playwright
        print("[OK] playwright")
    except ImportError:
        print("[FAIL] playwright missing")

    try:
        import pandas
        print("[OK] pandas")
    except ImportError:
        print("[FAIL] pandas missing")

    print("="*60)
    if all_files_ok:
        print("[OK] Environment looks GOOD.")
    else:
        print("[WARN] Enable to find some files.")

if __name__ == "__main__":
    test_env()
