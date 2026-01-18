# Test Config Documentation
**File:** `test/test_config.py`

## 🎯 Purpose
Verifies the `src/config_manager.py` logic. It ensures that:
1.  `config.json` is valid JSON.
2.  All required keys exist (`input_file`, `max_results`, etc.).
3.  Values have the correct data types (int, bool, string).
4.  Value ranges are reasonable (e.g., `max_results` isn't negative).
5.  Save/Load cycles works correctly.

## 🏃 How to Run
```powershell
python test/test_config.py
```

## ✅ Expected Output
```text
1. Checking if config file exists...
   [OK] config.json exists

2. Loading and parsing config...
   [OK] Config file is valid JSON
...
[PASS] CONFIG TEST PASSED
```

## 🐞 Common Failures
-   **JSON Decode Error**: syntax error in `config.json` (trailing comma is a common culprit).
-   **Missing Keys**: If you added a new feature but didn't update the config file, this test will warn you.
-   **Type Error**: e.g., `"max_results": "100"` (string) instead of `100` (int).
