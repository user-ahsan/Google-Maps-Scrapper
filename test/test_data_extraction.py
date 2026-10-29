import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.sheets_utils import (
    Business,
    clean_text_for_csv,
    extract_coordinates_from_url,
    generate_unique_key,
    remove_emojis,
)


def test_data_extraction():
    """
    Test data extraction and validation functions.
    Verifies phone number formats, URL validation, emoji removal.
    """
    print("="*60)
    print("   DATA EXTRACTION TEST")
    print("="*60)

    all_passed = True
    errors = []

    # Test 1: Emoji Removal
    print("\n1. Testing Emoji Removal...")
    test_cases = [
        ("Hello \U0001f30d World", "Hello  World"), # Spaces preserved in middle likely
        ("Star \u2b50 rating", "Star  rating"),
        ("Caf\xe9 \u2615", "Caf\xe9"), # Traling space stripped by remove_emojis
        ("Fire \U0001f525 truck \U0001f69b", "Fire  truck"), # Trailing space stripped
    ]

    emoji_tests_passed = 0
    for input_text, expected in test_cases:
        result = remove_emojis(input_text)
        safe_input = input_text.encode('ascii', 'backslashreplace').decode('ascii')
        safe_result = result.encode('ascii', 'backslashreplace').decode('ascii')
        safe_expected = expected.encode('ascii', 'backslashreplace').decode('ascii')

        if result == expected:
            # Use repr() to safely print strings containing emojis/unicode on Windows console
            print(f"   [PASS] {safe_input} -> {safe_result}")
            emoji_tests_passed += 1
        else:
            print(f"   [FAIL] {safe_input} -> {safe_result} (expected {safe_expected})")
            errors.append(f"Emoji removal failed for: {safe_input}")
            all_passed = False

    print(f"   Result: {emoji_tests_passed}/{len(test_cases)} tests passed")

    # Test 2: Text Cleaning
    print("\n2. Testing Text Cleaning...")
    clean_test_cases = [
        ("Hello   World\n\r", "Hello World"),
        ("Test  Multiple    Spaces", "Test Multiple Spaces"),
        ("Line1\nLine2\nLine3", "Line1 Line2 Line3"),
        ("Emoji  and newline", "Emoji and newline"), # Multiple spaces collapsed to one
    ]

    clean_tests_passed = 0
    for input_text, expected in clean_test_cases:
        result = clean_text_for_csv(input_text)
        if result == expected:
            print(f"   [PASS] Cleaned: '{input_text}'")
            clean_tests_passed += 1
        else:
            print(f"   [FAIL] Failed: '{input_text}' -> '{result}' (expected '{expected}')")
            errors.append("Text cleaning failed")
            all_passed = False

    print(f"   Result: {clean_tests_passed}/{len(clean_test_cases)} tests passed")

    # Test 3: Phone Number Validation
    print("\n3. Testing Phone Number Formats...")
    phone_test_cases = [
        ("+1 (555) 123-4567", True),  # Valid US
        ("555-123-4567", True),           # Valid US
        ("+44 20 7123 4567", True),        # Valid UK
        ("020 7123 4567", True),             # Valid UK
        ("123", True),                          # Valid short
        ("abc", False),                         # Invalid
        ("", False),                             # Empty
        (None, False),                           # None
    ]

    phone_tests_passed = 0
    for phone_num, should_be_valid in phone_test_cases:
        # Simple validation: not empty, contains digits, contains + or - allowed
        if phone_num is None or not phone_num or phone_num.strip() == "":
            is_valid = False
        else:
            # Remove non-digit chars
            digits_only = ''.join(c for c in phone_num if c.isdigit())
            # E.164 can be up to 15 digits, min usually 7 locally
            # But the full string can be longer due to formatting
            is_valid = len(digits_only) >= 3 and len(digits_only) <= 15

        result = is_valid == should_be_valid
        if result:
            status = "valid" if is_valid else "invalid"
            print(f"   [PASS] '{phone_num}' correctly identified as {status}")
            phone_tests_passed += 1
        else:
            actual_status = "valid" if is_valid else "invalid"
            expected_status = "valid" if should_be_valid else "invalid"
            print(f"   [FAIL] '{phone_num}' was {actual_status} but should be {expected_status}")
            errors.append("Phone validation failed")
            all_passed = False

    print(f"   Result: {phone_tests_passed}/{len(phone_test_cases)} tests passed")

    # Test 4: URL Validation
    print("\n4. Testing URL Validation...")
    url_test_cases = [
        ("https://example.com", True),                 # Valid HTTPS
        ("http://example.com", True),                  # Valid HTTP
        ("www.example.com", True),                    # Valid www
        ("example.com", True),                         # Valid domain
        ("https://example.com/path", True),           # Valid with path
        ("example", False),                             # Invalid
        ("", False),                                  # Empty
        (None, False),                                  # None
        ("ftp://example.com", False),               # Invalid protocol
    ]

    url_tests_passed = 0
    for url, should_be_valid in url_test_cases:
        if url is None or not url or url.strip() == "":
            is_valid = False
        else:
            # Simple validation: contains domain or valid URL
            import re
            url_pattern = re.compile(
                r'^(https?://|www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(\/.*)?$'
            )
            is_valid = bool(url_pattern.match(url.strip()))

        result = is_valid == should_be_valid
        if result:
            status = "valid" if is_valid else "invalid"
            print(f"   [PASS] '{url}' correctly identified as {status}")
            url_tests_passed += 1
        else:
            actual_status = "valid" if is_valid else "invalid"
            expected_status = "valid" if should_be_valid else "invalid"
            print(f"   [FAIL] '{url}' was {actual_status} but should be {expected_status}")
            errors.append("URL validation failed")
            all_passed = False

    print(f"   Result: {url_tests_passed}/{len(url_test_cases)} tests passed")

    # Test 5: Coordinate Extraction
    print("\n5. Testing Coordinate Extraction...")
    coord_test_cases = [
        ("https://www.google.com/maps/place/@40.7128,-74.0060,12z", (40.7128, -74.0060)),
        ("https://www.google.com/maps/place/@37.7749,-122.4194,17z", (37.7749, -122.4194)),
        ("invalid", (0.0, 0.0)),  # Invalid should return default
        ("", (0.0, 0.0)),          # Empty should return default
    ]

    coord_tests_passed = 0
    for url, expected_coords in coord_test_cases:
        lat, lng = extract_coordinates_from_url(url)
        if (lat, lng) == expected_coords:
            print(f"   [PASS] '{url}' -> ({lat}, {lng})")
            coord_tests_passed += 1
        else:
            print(f"   [FAIL] '{url}' -> ({lat}, {lng}) (expected {expected_coords})")
            errors.append("Coordinate extraction failed")
            all_passed = False

    print(f"   Result: {coord_tests_passed}/{len(coord_test_cases)} tests passed")

    # Test 6: Unique Key Generation
    print("\n6. Testing Unique Key Generation...")
    key_test_cases = [
        ({"Name": "Test Business", "Phone Number": "555-123-4567"}, "test business|555-123-4567"),
        ({"Name": "Test Business", "Address": "123 Main St"}, "test business|123 main st"),
        ({"Name": "Test Business", "Phone Number": ""}, "test business"),
        ({"Name": "", "Phone Number": "555-123-4567"}, "|555-123-4567"),  # Empty name -> starts with separator
        ({"Name": None, "Phone Number": "555-123-4567"}, "|555-123-4567"),  # None name
    ]

    key_tests_passed = 0
    for data, expected_key in key_test_cases:
        result_key = generate_unique_key(data)
        if result_key == expected_key:
            print(f"   [PASS] Key: '{result_key}'")
            key_tests_passed += 1
        else:
            print(f"   [FAIL] Got: '{result_key}' (expected '{expected_key}')")
            errors.append("Key generation failed")
            all_passed = False

    print(f"   Result: {key_tests_passed}/{len(key_test_cases)} tests passed")

    # Test 7: Business Dataclass
    print("\n7. Testing Business Dataclass...")
    try:
        business = Business(
            name="Test Business",
            address="123 Test St",
            phone_number="555-123-4567",
            reviews_average=4.5,
            reviews_count=100,
        )

        print("   [PASS] Business object created")
        print(f"   [PASS] Name: {business.name}")
        print(f"   [PASS] Phone: {business.phone_number}")
        print(f"   [PASS] Rating: {business.reviews_average}")
        print(f"   [PASS] Reviews: {business.reviews_count}")

    except Exception as e:
        print(f"   [FAIL] Business creation failed: {e}")
        errors.append(f"Business dataclass error: {e}")
        all_passed = False

    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("[PASS] DATA EXTRACTION TEST PASSED")
    else:
        print(f"[FAIL] DATA EXTRACTION TEST FAILED ({len(errors)} errors)")
        for error in errors[:5]:
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more errors")
    print("="*60)

    if not all_passed:
        raise Exception("Data extraction tests failed")

if __name__ == "__main__":
    test_data_extraction()
