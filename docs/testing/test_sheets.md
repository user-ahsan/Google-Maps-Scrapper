# Test Sheets Documentation
**File:** `test/test_sheets.py`

## 🎯 Purpose
Isolates the **Google Sheets API** connection. It verifies:
1.  Authentication using `credentials.json`.
2.  Accessing the specific spreadsheet (`Gmaps Leads`).
3.  **Permissions**: Writing a random test value to cell `Z1`, reading it back, and verifying it matches.

## 🏃 How to Run
```powershell
python test/test_sheets.py
```

## ✅ Expected Output
```text
1. Authenticating...
✅ Authenticated.
2. Opening Sheet 'Gmaps Leads'...
✅ Sheet Open: ...
3. Writing Test Data...
✅ Written 'TEST_CONN_1234' to Z1
4. Reading Test Data...
✅ Read Verification Successful
...
🎉 SHEETS TEST COMPLETE
```

## 🐞 Common Failures
-   **APIError**: "Insufficient Permission". Make sure you have **shared the Google Sheet** with the Service Account Email (found in `credentials.json`).
-   **SpreadsheetNotFound**: The name in the code must match the name in Google Drive exactly.
-   **Token Expired**: System clock skew or bad credentials.
