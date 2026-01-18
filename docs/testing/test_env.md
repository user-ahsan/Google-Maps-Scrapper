# Test Environment Documentation
**File:** `test/test_env.py`

## 🎯 Purpose
The **Environment Sanity Check**. This should be the *first* test you run after setting up the project. It checks:
1.  Python version.
2.  Critical files existence (`credentials.json`, `input.txt`, scripts).
3.  Library imports (`playwright`, `pandas`, `gspread`).

## 🏃 How to Run
```powershell
python test/test_env.py
```

## ✅ Expected Output
```text
   ENVIRONMENT TEST   
Python Version: 3.x.x
[OK] credentials.json
[OK] input.txt
...
Checking Libraries...
[OK] gspread
[OK] playwright
[OK] pandas
[OK] Environment looks GOOD.
```

## 🐞 Common Failures
-   **Missing Modules**: If `[FAIL] playwright missing`, run `pip install -r requirements.txt`.
-   **Missing Credentials**: If `[FAIL] credentials.json`, you must place your Google Cloud Service Account JSON key in the root directory.
