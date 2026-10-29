import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config_manager import ConfigManager


def test_config():
    """
    Test configuration file validation.
    Verifies config exists, is valid JSON, and has all required keys.
    """
    print("="*60)
    print("   CONFIG FILE VALIDATION TEST")
    print("="*60)

    config_file = "config.json"

    # Test 1: Config file exists
    print("\n1. Checking if config file exists...")
    if os.path.exists(config_file):
        print(f"   [OK] {config_file} exists")
    else:
        print(f"   [WARN] {config_file} not found (will use defaults)")

    # Test 2: Load and parse JSON
    print("\n2. Loading and parsing config...")
    try:
        with open(config_file) as f:
            _ = json.load(f)
            print("   [OK] Config file is valid JSON")
    except json.JSONDecodeError as e:
        print(f"   [FAIL] JSON Decode Error: {e}")
        raise
    except FileNotFoundError:
        print("   [WARN] Config file not found (will use defaults)")
    except Exception as e:
        print(f"   [FAIL] Error loading config: {e}")
        raise

    # Test 3: Required keys present
    print("\n3. Checking required keys...")
    config_manager = ConfigManager(config_file)
    required_keys = [
        "input_file", "creds_file", "max_results", "headless",
        "sheet_behavior", "max_scroll_time", "max_scroll_retries",
        "theme", "export_csv"
    ]

    all_present = True
    for key in required_keys:
        if key in config_manager.config:
            print(f"   [OK] {key}")
        else:
            print(f"   [FAIL] {key} MISSING")
            all_present = False

    if all_present:
        print("\n   [OK] All required keys present")
    else:
        print("\n   [FAIL] Some required keys missing")

    # Test 4: Validate value types
    print("\n4. Validating value types...")
    type_errors = []

    # Validate numeric types
    numeric_keys = {
        "max_results": int,
        "max_scroll_time": int,
        "max_scroll_retries": int,
    }

    for key, expected_type in numeric_keys.items():
        value = config_manager.get(key)
        if value is None:
            continue
        try:
            expected_type(value)
            print(f"   [OK] {key} = {value} ({expected_type.__name__})")
        except (ValueError, TypeError):
            error_msg = f"{key} = {value} (expected {expected_type.__name__})"
            print(f"   [FAIL] {error_msg}")
            type_errors.append(error_msg)

    # Validate boolean types
    bool_keys = {
        "headless": bool,
        "export_csv": bool,
    }

    for key, expected_type in bool_keys.items():
        value = config_manager.get(key)
        if value is None:
            continue
        if isinstance(value, bool):
            print(f"   [OK] {key} = {value} ({expected_type.__name__})")
        else:
            error_msg = f"{key} = {value} (expected {expected_type.__name__})"
            print(f"   [FAIL] {error_msg}")
            type_errors.append(error_msg)

    # Validate enum types
    enum_keys = {
        "sheet_behavior": ["Append", "Overwrite", "New Sheet"],
        "theme": ["Dark", "Light", "System"],
    }

    for key, valid_values in enum_keys.items():
        value = config_manager.get(key)
        if value is None:
            continue
        if value in valid_values:
            print(f"   [OK] {key} = {value} (valid)")
        else:
            error_msg = f"{key} = {value} (expected one of {valid_values})"
            print(f"   [FAIL] {error_msg}")
            type_errors.append(error_msg)

    # Test 5: Validate ranges
    print("\n5. Validating value ranges...")
    range_errors = []

    # max_results should be reasonable
    max_results = config_manager.get("max_results")
    if max_results and int(max_results) > 100000:
        error_msg = f"max_results = {max_results} (should be <= 100000)"
        print(f"   [WARN] {error_msg}")
        range_errors.append(error_msg)
    elif max_results:
        print(f"   [OK] max_results = {max_results} (reasonable)")

    # max_scroll_time should be positive
    max_scroll_time = config_manager.get("max_scroll_time")
    if max_scroll_time and int(max_scroll_time) <= 0:
        error_msg = f"max_scroll_time = {max_scroll_time} (should be > 0)"
        print(f"   [FAIL] {error_msg}")
        range_errors.append(error_msg)
    elif max_scroll_time:
        print(f"   [OK] max_scroll_time = {max_scroll_time}s (positive)")

    # max_scroll_retries should be reasonable
    max_scroll_retries = config_manager.get("max_scroll_retries")
    if max_scroll_retries and int(max_scroll_retries) > 20:
        error_msg = f"max_scroll_retries = {max_scroll_retries} (should be <= 20)"
        print(f"   [WARN] {error_msg}")
        range_errors.append(error_msg)
    elif max_scroll_retries:
        print(f"   [OK] max_scroll_retries = {max_scroll_retries} (reasonable)")

    # Test 6: Test save/load cycle
    print("\n6. Testing save/load cycle...")
    try:
        test_key = "test_key_12345"
        test_value = "test_value_67890"

        # Save
        config_manager.set(test_key, test_value)

        # Load new instance
        new_config = ConfigManager(config_file)
        loaded_value = new_config.get(test_key)

        # Clean up
        if test_key in new_config.config:
            del new_config.config[test_key]
        new_config._save_to_disk()

        if loaded_value == test_value:
            print("   [OK] Save/Load cycle working")
        else:
            print(f"   [FAIL] Save/Load cycle failed (got {loaded_value})")
            type_errors.append("Save/Load cycle failed")
    except Exception as e:
        print(f"   [FAIL] Save/Load cycle error: {e}")
        type_errors.append(f"Save/Load cycle error: {e}")

    # Summary
    print("\n" + "="*60)
    total_errors = len(type_errors) + len(range_errors)
    if total_errors == 0:
        print("[PASS] CONFIG TEST PASSED")
    else:
        print(f"[FAIL] CONFIG TEST FAILED ({total_errors} errors)")
    print("="*60)

    if total_errors > 0:
        raise Exception("Config validation failed")

if __name__ == "__main__":
    test_config()
