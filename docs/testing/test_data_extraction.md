# Test Data Extraction Documentation
**File:** `test/test_data_extraction.py`

## 🎯 Purpose
This test suite verifies the **robustness and accuracy** of the data cleaning and validation functions used in the scraper. It works in isolation from the browser and internet, focusing purely on string manipulation logic.

## 🔍 Key Functions Tested
1.  **Emoji Removal**: verifying `remove_emojis()` correctly strips unicode characters while preserving text.
2.  **Text Cleaning**: Verifying `clean_text_for_csv()` handles whitespace, newlines, and separators.
3.  **Phone Validation**: Ensuring `validate_phone()` correctly identifies valid vs. invalid formats.
4.  **URL Extraction**: Testing coordinate parsing from Google Maps URLs.
5.  **Key Generation**: Verifying `generate_unique_key()` produces consistent IDs for deduplication.

## 🏃 How to Run
Run via pytest for detailed assertions:
```powershell
python -m pytest test/test_data_extraction.py
```
Or directly:
```powershell
python test/test_data_extraction.py
```

## ✅ Expected Output
You should see a series of `[PASS]` indicators.
```text
   DATA EXTRACTION TEST
1. Testing Emoji Removal...
   [PASS] 'Hello \U0001f30d World' -> 'Hello  World'
   ...
2. Testing Text Cleaning...
   ...
[PASS] DATA EXTRACTION TEST PASSED
```

## 🐞 Common Failures & Debugging
-   **UnicodeEncodeError**: If this occurs, it means the safely-encoded print statements logic has been bypassed or the console encoding is extremely restricted. The current version uses `backslashreplace` to prevent this.
-   **AssertionError**:
    -   *Phone Validation*: If valid phones are marked invalid, check the `src/sheets_utils.py` logic. We enforce a length check (3-15 digits).
    -   *Key Generation*: Ensure the test expectation matches the normalization logic (lowercase names, pipe `|` separators).
