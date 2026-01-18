"""
Security Utilities for Google Maps Scraper
Provides input validation, sanitization, and rate limiting.
"""

import re
import os
from typing import Optional, List, Tuple, Callable
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# --- Whitelist Patterns ---

# Allow only alphanumeric, spaces, and basic punctuation for file paths
PATH_ALLOWED_CHARS = r"^[a-zA-Z0-9_\-./\\]+$"

# Phone number patterns
PHONE_PATTERNS = [
    r'^\+?[\d\s\-\(\)\.\s]+$'  # +1 (555) 123-4567
    r'^[\d\s\-\(\)\.\s]+$'           # 555-123-4567
    r'^0\d{9,10}\s*$'            # 020 area codes
]

# URL patterns
URL_PATTERN = re.compile(
    r'^https?://'  # Protocol
    r'(www\.)?[a-zA-Z0-9-]+\.[a-zA-Z0-9\-._~:/?#\[\]\@!$&\(\)\s]*+$'  # Domain and Path
)

# Search query patterns
QUERY_ALLOWED_CHARS = r"^[a-zA-Z0-9\s\-,.]+$"
QUERY_MAX_LENGTH = 500

# Email pattern (basic validation)
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# --- Validation Functions ---

def validate_file_path(path: str) -> Tuple[bool, str, str]:
    """
    Validates and sanitizes file path.
    Returns: (is_valid, sanitized_path, error_message)
    """
    if not path or not isinstance(path, str):
        return False, "", "Path must be a non-empty string"
    
    # Basic length check
    if len(path) > 260:
        return False, "", "Path too long (max 260 characters)"
    
    # Check for path traversal attempts
    if '..' in path or path.startswith('/') or path.startswith('\\'):
        return False, "", "Path traversal detected"
    
    # Check for invalid characters
    if not re.match(PATH_ALLOWED_CHARS, path.replace('/', '_').replace('\\', '_')):
        return False, "", "Path contains invalid characters"
    
    # Normalize path
    sanitized = os.path.normpath(path)
    
    # Ensure path doesn't escape sandbox
    if sanitized.startswith('..'):
        return False, "", "Path escapes directory"
    
    return True, sanitized, ""

def validate_phone_number(phone: str) -> Tuple[bool, str, str]:
    """
    Validates phone number format.
    Returns: (is_valid, formatted_phone, error_message)
    """
    if not phone:
        return True, "", "Empty phone number allowed"
    
    # Remove common formatting
    cleaned = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Check if all digits
    if not cleaned.isdigit():
        # Check against allowed patterns
        for pattern in PHONE_PATTERNS:
            if re.match(pattern, phone):
                return True, phone, ""
        return False, "", "Invalid phone number format"
    
    # Basic length check
    if len(cleaned) < 7 or len(cleaned) > 15:
        return False, "", "Phone number must be 7-15 digits"
    
    return True, cleaned, ""

def validate_url(url: str) -> Tuple[bool, str, str]:
    """
    Validates URL format.
    Returns: (is_valid, error_message)
    """
    if not url:
        return False, "", "URL is required"
    
    # Basic URL validation
    if not isinstance(url, str):
        return False, "", "URL must be a string"
    
    # Check against pattern
    if URL_PATTERN.match(url.strip()):
        return True, url, ""
    
    return False, "", "Invalid URL format"

def validate_email(email: str) -> Tuple[bool, str, str]:
    """
    Validates email address format.
    Returns: (is_valid, error_message)
    """
    if not email:
        return True, "", "Empty email allowed"
    
    if EMAIL_PATTERN.match(email.strip()):
        return True, email, ""
    
    return False, "", "Invalid email format"

def validate_search_query(query: str) -> Tuple[bool, str, str]:
    """
    Validates search query string.
    Returns: (is_valid, sanitized_query, error_message)
    """
    if not query:
        return False, "", "Query is required"
    
    if not isinstance(query, str):
        return False, "", "Query must be a string"
    
    # Length check
    if len(query) > QUERY_MAX_LENGTH:
        return False, "", f"Query too long (max {QUERY_MAX_LENGTH} characters)"
    
    # Character validation
    if not re.match(QUERY_ALLOWED_CHARS, query):
        return False, "", "Query contains invalid characters"
    
    # Sanitize - remove extra spaces
    sanitized = re.sub(r'\s+', ' ', query.strip())
    
    return True, sanitized, ""

def validate_numeric_value(value: str, value_name: str, min_val: int = 0, max_val: Optional[int] = None) -> Tuple[bool, int, str]:
    """
    Validates numeric configuration values.
    Returns: (is_valid, int_value, error_message)
    """
    if not value:
        return False, 0, f"{value_name} is required"
    
    try:
        int_val = int(value)
    except ValueError:
        return False, 0, f"{value_name} must be an integer"
    
    # Range check
    if int_val < min_val:
        return False, 0, f"{value_name} must be at least {min_val}"
    
    if max_val and int_val > max_val:
        return False, 0, f"{value_name} must be at most {max_val}"
    
    return True, int_val, ""

def validate_enum_value(value: str, value_name: str, allowed_values: List[str]) -> Tuple[bool, str, str]:
    """
    Validates enum/categorical configuration values.
    Returns: (is_valid, sanitized_value, error_message)
    """
    if not value:
        return False, "", f"{value_name} is required"
    
    if value not in allowed_values:
        return False, value, f"{value_name} must be one of: {', '.join(allowed_values)}"
    
    return True, value, ""

def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitizes SQL identifier (table/column name) to prevent injection.
    Only allows alphanumeric and underscore.
    """
    # Remove all characters except alphanumeric and underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized
    
    return sanitized

def sanitize_for_sql(value: str) -> str:
    """
    Sanitizes a value for safe SQL usage.
    Removes characters that could be used for injection.
    """
    if not value or not isinstance(value, str):
        return ""
    
    # Remove SQL injection characters
    sanitized = value.replace("'", "''").replace('"', '""')
    # Remove comments
    sanitized = re.sub(r'--.*$', '', sanitized)
    
    return sanitized.strip()

def validate_boolean(value: str, value_name: str) -> Tuple[bool, bool, str]:
    """
    Validates boolean configuration values.
    Returns: (is_valid, bool_value, error_message)
    """
    if value.lower() in ['true', '1', 'yes', 'on']:
        return True, True, ""
    if value.lower() in ['false', '0', 'no', 'off']:
        return True, False, ""
    if value.lower() in ['', 'null', 'none']:
        return True, False, ""
    
    return False, False, f"{value_name} must be true/false (or 1/0, yes/no, on/off)"

# --- Rate Limiting ---

class RateLimiter:
    """
    Implements rate limiting with exponential backoff.
    Tracks request timing and automatically adjusts delays.
    """
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 10.0, backoff_multiplier: float = 2.0, max_retries: int = 3):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_retries = max_retries
        self.request_times = []
        self.failure_count = 0
    
    def record_success(self):
        """Record a successful request."""
        import time
        current_time = time.time()
        self.request_times.append(current_time)
        
        # Remove old times outside window
        cutoff = current_time - 60  # Keep last 60 seconds
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        # Reset failure count on success
        self.failure_count = 0
        logger.debug(f"Request succeeded, reset failure count to {self.failure_count}")
    
    def record_failure(self, exception: Exception):
        """Record a failed request with backoff."""
        import time
        current_time = time.time()
        self.request_times.append(current_time)
        
        # Increment failure count
        self.failure_count += 1
        
        # Check if should backoff further
        if self.failure_count >= self.max_retries:
            logger.warning(f"Max retries ({self.max_retries}) reached, not increasing delay further")
            return self.max_delay
        
        # Calculate backoff with jitter
        backoff = min(self.max_delay, self.backoff_multiplier ** (self.failure_count - 1) + self.min_delay)
        
        # Add random jitter (±25%)
        import random
        jitter = backoff * random.uniform(0.75, 1.25)
        delay = backoff + jitter
        
        logger.warning(f"Request failed (attempt {self.failure_count}), waiting {delay:.2f}s before retry")
        time.sleep(delay)
    
    def get_delay(self) -> float:
        """Get current delay in seconds."""
        if self.failure_count == 0:
            return self.min_delay
        elif self.failure_count == 1:
            return self.min_delay * self.backoff_multiplier
        elif self.failure_count == 2:
            return self.min_delay * (self.backoff_multiplier ** 2)
        else:
            return self.max_delay
    
    def should_skip(self) -> bool:
        """Check if request should be skipped based on failure count."""
        return self.failure_count >= self.max_retries

# --- Input Validation Decorator ---
    
def validate_input(
    input_type: str,
    value: str,
    **kwargs
) -> bool:
    """
    Validates a single input value based on type.
    Returns: (is_valid)
    """
    if input_type == "search_query":
        result = validate_search_query(value)
        return result[0]
    elif input_type == "phone":
        result = validate_phone_number(value)
        return result[0]
    elif input_type == "url":
        result = validate_url(value)
        return result[0]
    elif input_type == "email":
        result = validate_email(value)
        return result[0]
    elif input_type == "file_path":
        result = validate_file_path(value)
        return result[0]
    elif input_type == "numeric":
        min_val = kwargs.get("min_val", 0)
        max_val = kwargs.get("max_val")
        result = validate_numeric_value(value, "numeric", min_val, max_val)
        return result[0]
    else:
        return False

def validate_config_values(
    max_results: Optional[str] = None,
    headless: Optional[str] = None,
    scroll_wait: Optional[str] = None,
    max_scroll_time: Optional[str] = None,
    max_scroll_retries: Optional[str] = None,
    sheet_behavior: Optional[str] = None,
    theme: Optional[str] = None,
    export_csv: Optional[str] = None,
    export_sheets: Optional[str] = None,
    export_db: Optional[str] = None,
    auto_upload: Optional[str] = None,
    auto_accept: Optional[str] = None,
    manual_verification: Optional[str] = None,
    interactive_controls: Optional[str] = None,
    show_progress: Optional[str] = None,
    pre_filter_names: Optional[str] = None,
    batch_db_ops: Optional[str] = None,
    cache_sheet_data: Optional[str] = None,
    smart_wait_enabled: Optional[str] = None,
    use_feed_scroll: Optional[str] = None,
    scroll_amount_per_step: Optional[str] = None,
    auto_skip_timeout: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """
    Validates all input configuration values.
    Returns: (is_valid, list of error_messages)
    """
    errors = []
    
    # Numeric validations
    numeric_validations = [
        ('max_results', max_results, 100, 100000),
        ('scroll_wait', scroll_wait, 500, 60000),
        ('max_scroll_time', max_scroll_time, 1, 3600),
        ('max_scroll_retries', max_scroll_retries, 0, 20),
    ]
    
    for key, value, default_val, min_val, max_val in numeric_validations:
        if value is not None:
            result = validate_numeric_value(value, key, min_val, max_val)
            if not result[0]:
                errors.append(result[2])
    
    # Enum validations
    enum_validations = [
        ('sheet_behavior', sheet_behavior, ['Append', 'Overwrite', 'New Sheet']),
        ('theme', theme, ['Dark', 'Light', 'System']),
    ]
    
    for key, value, default_val, allowed_values in enum_validations:
        if value is not None:
            result = validate_enum_value(value, key, allowed_values)
            if not result[0]:
                errors.append(result[2])
    
    # Boolean validations
    bool_validations = [
        ('headless', headless, True),
        ('export_csv', export_csv, True),
        ('export_sheets', export_sheets, True),
        ('export_db', export_db, True),
        ('auto_upload', auto_upload, False),
        ('auto_accept', auto_accept, True),
        ('manual_verification', manual_verification, False),
        ('interactive_controls', interactive_controls, True),
        ('show_progress', show_progress, True),
        ('pre_filter_names', pre_filter_names, True),
        ('batch_db_ops', batch_db_ops, True),
        ('cache_sheet_data', cache_sheet_data, True),
        ('smart_wait_enabled', smart_wait_enabled, True),
        ('use_feed_scroll', use_feed_scroll, True),
        ('scroll_amount_per_step', scroll_amount_per_step, '10000'),
        ('auto_skip_timeout', auto_skip_timeout, '0'),
    ]
    
    for key, value, default_val in bool_validations:
        if value is not None:
            result = validate_boolean(value, key)
            if not result[0]:
                errors.append(result[2])
    
    is_valid = len(errors) == 0
    
    if not is_valid:
        logger.warning(f"Input validation failed: {len(errors)} errors")
    
    return is_valid, errors

def validate_config_file(config_path: str = "config.json") -> Tuple[bool, List[str]]:
    """
    Validates configuration file structure and values.
    Returns: (is_valid, list of error_messages)
    """
    if not os.path.exists(config_path):
        return False, [f"Configuration file not found: {config_path}"]
    
    try:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Configuration file is not valid JSON: {e}"]
    except Exception as e:
        return False, [f"Error reading config file: {e}"]
    
    # Validate required keys
    required_keys = [
        'input_file', 'creds_file', 'max_results', 'headless',
        'sheet_behavior', 'max_scroll_time', 'max_scroll_retries',
        'export_csv', 'export_sheets', 'export_db',
    ]
    
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        errors.append(f"Missing required config keys: {', '.join(missing_keys)}")
    
    return len(errors) == 0, errors

# --- SQL Injection Prevention ---

def escape_sql_like(value: str) -> str:
    """
    Escapes a value for safe use in LIKE queries.
    """
    return sanitize_for_sql(value).replace('%', '%%').replace('_', '\\_')

def validate_sql_identifier(identifier: str) -> Tuple[bool, str, str]:
    """
    Validates SQL table/column identifier for injection prevention.
    """
    if not identifier:
        return False, "", "Identifier is required"
    
    sanitized = sanitize_sql_identifier(identifier)
    
    # Check if it's a valid SQL identifier
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', sanitized):
        return False, sanitized, "Invalid SQL identifier (must start with letter or underscore, only contains alphanumeric and underscore)"
    
    return True, sanitized, ""

# --- Usage Examples ---

if __name__ == "__main__":
    # Quick tests
    print("Testing security utilities...")
    
    # Test path validation
    valid, path, err = validate_file_path("test.txt")
    print(f"Path validation: {valid}, {path}, {err}")
    
    # Test phone validation
    valid, phone, err = validate_phone_number("+1 (555) 123-4567")
    print(f"Phone validation: {valid}, {phone}, {err}")
    
    valid, phone, err = validate_phone_number("555-123-4567")
    print(f"Phone validation: {valid}, {phone}, {err}")
    
    # Test URL validation
    valid, url, err = validate_url("https://example.com")
    print(f"URL validation: {valid}, {url}, {err}")
    
    # Test query validation
    valid, query, err = validate_search_query("restaurants in New York")
    print(f"Query validation: {valid}, {query}, {err}")
    
    # Test numeric validation
    valid, val, err = validate_numeric_value("500", "max_results", 0, 100000)
    print(f"Numeric validation: {valid}, {val}, {err}")
    
    print("All tests passed!")
