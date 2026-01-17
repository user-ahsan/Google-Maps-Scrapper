# Google Maps Scraper - Issues & Improvements

This document identifies all issues, bugs, security vulnerabilities, and improvements needed for the Google Maps Scraper project.

---

## 🔴 CRITICAL SECURITY VULNERABILITIES

### 1. Credentials Exposed in Git Repository
- **Issue**: `credentials.json` (Google Service Account with private key) is committed to git
- **Impact**: Full access to user's Google Sheets can be stolen
- **File**: `credentials.json:1-14`
- **Fix**: Revoke credentials, remove from git history (`git filter-branch`), add to `.gitignore` properly
- **Priority**: 🔴 IMMEDIATE

### 2. No Input Validation/Sanitization
- **Issue**: User input from GUI/CLI not sanitized before use
- **Impact**: Command injection, XSS in data, file path traversal attacks
- **Files**: `gui_app.py:303`, `main.py:229`, `leads_scrapping.py:78`
- **Fix**: 
  - Validate all user inputs with allowlists
  - Sanitize file paths using `os.path.normpath()` and `os.path.abspath()`
  - Use `shlex.quote()` for command arguments
  - Add input validation decorator
- **Priority**: 🔴 IMMEDIATE

### 3. SQL Injection Risk
- **Issue**: While mostly using parameterized queries, some edge cases exist in table creation
- **Impact**: Potential SQL injection if user data reaches table/column names
- **File**: `db.py:22-43` (table creation uses f-strings)
- **Fix**:
  - Use `identifier()` from sqlite3 for table/column names
  - Add input validation for all dynamic SQL components
  - Use only parameterized queries for user data
- **Priority**: 🔴 IMMEDIATE

### 4. No Rate Limiting
- **Issue**: Can spam Google Maps without delays
- **Impact**: IP ban, account suspension, scraping detected
- **File**: `leads_scrapping.py:139` (hardcoded 3s wait only)
- **Fix**:
  - Add configurable rate limiting with exponential backoff
  - Track request timing and auto-adjust delays
  - Add random jitter to avoid detection
  - Implement circuit breaker on repeated failures
- **Priority**: 🔴 IMMEDIATE

---

## 🟠 CRITICAL BUGS

### 5. Duplicate Browser Launch
- **Issue**: Browser launched twice due to duplicate code
- **Code**: `main.py:233-234`
  ```python
  browser = p.chromium.launch(headless=not args.headed)
  browser = p.chromium.launch(headless=not args.headed)  # DUPLICATE
  ```
- **Impact**: Wastes resources, leaks memory, potential crash
- **Fix**: Remove line 234
- **Priority**: 🟠 HIGH

### 6. Duplicate Page Navigation
- **Issue**: Google Maps URL loaded twice
- **Code**: `main.py:251-253`
  ```python
  page.goto("https://www.google.com/maps", timeout=20000)
  page.goto("https://www.google.com/maps", timeout=20000)  # DUPLICATE
  ```
- **Impact**: Wastes 20 seconds per query, poor UX
- **Fix**: Remove line 253
- **Priority**: 🟠 HIGH

### 7. Dead Code
- **Issue**: Unreachable return statement after function already returned
- **Code**: `sheets_utils.py:604`
  ```python
  return seen_urls  # Function returns here
  return known_names_local  # NEVER REACHED
  ```
- **Impact**: Confuses maintainers, code never executed
- **Fix**: Remove line 604
- **Priority**: 🟠 HIGH

### 8. Undefined Variable
- **Issue**: `check_name` variable not defined in all code paths
- **Code**: `leads_scrapping.py:320`
  ```python
  business.name = check_name or "Unknown"  # check_name may be undefined
  ```
- **Root Cause**: Duplicate variable assignment at lines 226-229, second overwrites first but may not execute
- **Impact**: Crash when certain extraction paths are taken
- **Fix**: Ensure `check_name` is always defined before line 320, remove duplicate code
- **Priority**: 🟠 HIGH

### 9. Unreachable Code Due to Early Return
- **Issue**: Multiple return statements, second one never reached
- **Code**: `sheets_utils.py:598-604`
  ```python
  except Exception:
      pass
  
  return known_names_local  # AFTER FUNCTION ALREADY RETURNED AT LINE 600
  ```
- **Impact**: Dead code, confusion for maintainers
- **Fix**: Remove unreachable return statement
- **Priority**: 🟠 HIGH

---

## 🟠 BROKEN/INCOMPLETE FEATURES

### 10. Resume Functionality Flawed
- **Issue**: No validation of job state file integrity
- **Code**: `job_manager.py:73-76`
  ```python
  def has_unfinished_job(self):
      return (self.current_state["status"] != "COMPLETED" and 
              len(self.current_state["pending_queries"]) > 0)
  ```
- **Problems**:
  - Doesn't check if job state file is corrupted
  - No validation that pending queries are still valid
  - No checksum validation
- **Impact**: Resume may fail or corrupt further
- **Fix**:
  - Add state file validation with JSON schema
  - Add checksum verification
  - Add recovery mode for corrupted files
  - Validate each pending query before resuming
- **Priority**: 🟠 HIGH

### 11. Controller Signals Ignored
- **Issue**: `StopScrapingException` not caught in all places, some loops ignore controller checks
- **Files**: `leads_scrapping.py:317`, `main_gui_wrapper.py:108-110`
- **Impact**: Stop button may not work, leads to unresponsive GUI
- **Fix**:
  - Add controller checks in all loops
  - Wrap all long operations with controller checks
  - Add proper exception handling for stop signals
  - Test stop functionality end-to-end
- **Priority**: 🟠 HIGH

### 12. GUI Diagnostics Only Runs Default Settings
- **Issue**: Diagnostics button in GUI always runs `main.run_diagnostics(force_offline=True)`, skips Sheets test
- **File**: `gui_app.py:462`
  ```python
  main.run_diagnostics(force_offline=True)  # Always forces offline
  ```
- **Problems**:
  - Cannot test Google Sheets connection
  - No way to select which tests to run
  - No feedback on which tests pass/fail
  - Missing test files for:
    - Config file validation
    - Headless scraping with example data
    - Headed scraping with example data
    - Data extraction validation
- **Impact**: Users cannot properly diagnose issues, cannot test all components
- **Fix Required**:
  - Create `test/test_config.py` - Config validation tests
  - Create `test/test_headless_scrape.py` - Headless scraping test
  - Create `test/test_headed_scrape.py` - Headed scraping test
  - Create `test/test_data_extraction.py` - Data extraction tests
  - Update `gui_app.py:run_diagnostics_gui()` to:
    - Show test selection popup with checkboxes
    - Allow user to enable/disable individual tests
    - Run selected tests in sequence
    - Show pass/fail status for each test
    - Use current config settings instead of forcing offline mode
- **Priority**: 🟠 HIGH

### 13. Missing Scrolling Configuration in GUI
- **Issue**: Scrolling configuration not exposed in GUI settings
- **Missing Config Options**:
  - `scroll_amount_per_step` - Pixels per scroll (default: 10000)
  - `auto_skip_timeout` - Auto-skip after N seconds (0 = disabled)
  - `smart_wait_enabled` - Use smart element detection (default: True)
  - `use_feed_scroll` - Use feed scroll vs global scroll (default: True)
- **Existing But Exposed**:
  - `scroll_wait` - Wait time between scrolls (ms)
  - `max_scroll_time` - Total time limit (seconds)
  - `max_scroll_retries` - Max no-change retries
- **Impact**: Users cannot optimize scrolling behavior, may waste time or miss data
- **Fix Required**:
  - Add missing options to `src/config_manager.py:DEFAULT_CONFIG`
  - Add GUI fields in `gui_app.py:create_settings_frame()`:
    - Scroll Amount Per Step (pixels) - Number input
    - Auto-Skip Timeout (seconds) - Number input (0 = disabled)
    - Smart Wait - Checkbox (enable/disable element detection)
    - Feed Scroll Mode - Checkbox (use feed scroll vs global scroll)
  - Update `src/leads_scrapping.py:scrape_data()` to:
    - Accept all new scroll parameters
    - Implement smart wait logic with element detection
    - Implement auto-skip timeout
    - Support both feed and global scroll modes
- **Priority**: 🟠 HIGH

### 14. Missing Feature Toggles in GUI
- **Issue**: No GUI controls for enabling/disabling features
- **Missing Toggle Categories**:
  
  **Data Export Toggles:**
  - Enable CSV Export (boolean)
  - Enable Sheets Sync (boolean)
  - Enable Database Save (boolean)
  - Auto-upload on complete (boolean)
  
  **Behavior Toggles:**
  - Auto-accept URLs (boolean)
  - Manual verification (boolean)
  - Interactive controls enabled (boolean)
  - Show progress bars (boolean)
  
  **Performance Toggles:**
  - Pre-filter by known names (boolean)
  - Smart wait for element load (boolean)
  - Batch database operations (boolean)
  - Cache sheet data (boolean)
- **Impact**: Users cannot control behavior/performance, must edit config file manually
- **Fix Required**:
  - Add all toggle options to `src/config_manager.py:DEFAULT_CONFIG`
  - Add GUI sections in `gui_app.py:create_settings_frame()`:
    - Data Export section with 4 checkboxes
    - Behavior section with 4 checkboxes
    - Performance section with 4 checkboxes
  - Update `main_gui_wrapper.py:run_gui_mode()` to use new toggle values
  - Update scraping logic to respect toggle settings
- **Priority**: 🟠 HIGH

---

## 🟡 OPTIMIZATION ISSUES

### 15. Database Queries in Loops
- **Issue**: `get_known_names()` called multiple times per query instead of once
- **Code**:
  ```python
  # main.py:269
  known_names_local = db.get_known_names()
  
  # main_gui_wrapper.py:116
  known_names_local = db.get_known_names()
  ```
- **Impact**: N+1 query problem, slow for large datasets (10,000+ records)
- **Fix**:
  - Load known_names once at job start
  - Cache results in memory
  - Refresh only when new data is added
  - Use job_manager to cache across queries
- **Priority**: 🟡 MEDIUM

### 16. Inefficient Deduplication
- **Issue**: Loads separate sets for names and keys instead of combined query
- **Problems**:
  - Sheets API fetches all rows repeatedly for each query
  - No caching of sheet data between queries
  - Separate lookups for names vs keys
- **Files**: `main.py:271-277`, `main_gui_wrapper.py:116-121`
- **Impact**: Wastes API quota, slow performance
- **Fix**:
  - Batch fetch all sheet data once at job start
  - Create combined index (name + key) in memory
  - Implement incremental updates (only fetch new rows)
  - Use cache with TTL for sheet data
- **Priority**: 🟡 MEDIUM

### 17. Memory Inefficiency
- **Issue**: Loads entire CSV/Sheets into memory without streaming
- **Code**:
  ```python
  df = pd.read_csv(target_csv)  # Loads entire file
  all_values = worksheet.get_all_values()  # Loads entire sheet
  ```
- **Impact**: Memory exhaustion with large datasets (100,000+ records)
- **Fix**:
  - Use `pd.read_csv(chunksize=5000)` for large CSVs
  - Implement streaming for Sheets API
  - Use generators instead of lists where possible
  - Clean up DataFrames after use
- **Priority**: 🟡 MEDIUM

### 18. Inefficient Scrolling
- **Issue**: Fixed wait time regardless of actual load completion
- **Code**: `leads_scrapping.py:135-139`
  ```python
  page.locator(feed_selector).evaluate("node => node.scrollTop += 10000")
  page.wait_for_timeout(scroll_wait)  # Fixed 3s wait - wasteful
  ```
- **Problems**:
  - Waits full 3s even if loaded in 500ms
  - No detection of actual load completion
  - No smart wait for new elements
- **Impact**: Wastes time, slower scraping
- **Fix**:
  - Implement smart wait with element detection
  - Use `wait_for_selector()` for new listings
  - Poll for count changes with shorter intervals
  - Add early exit when no new elements detected
- **Priority**: 🟡 MEDIUM

### 19. Unnecessary User-Agent Randomization
- **Issue**: User-Agent changed every run
- **Code**: `main.py:242`
  ```python
  ua = ua_gen.random  # Different every run
  ```
- **Impact**:
  - Breaks deterministic behavior
  - Inconsistent scraping results
  - May trigger bot detection
- **Fix**:
  - Use consistent User-Agent across runs
  - Store UA in config file
  - Only rotate if blocked (fallback mechanism)
- **Priority**: 🟡 MEDIUM

### 20. No Connection Pooling
- **Issue**: Creates new database connection for every operation
- **Code**: `db.py:8-13`, `db.py:52-89`, `db.py:91-107`
  ```python
  def get_db_connection():  # Called every time
      conn = sqlite3.connect(DB_PATH)
      conn.row_factory = sqlite3.Row
      return conn
  ```
- **Impact**: Connection overhead, slower performance, possible connection limits
- **Fix**:
  - Implement connection pool
  - Reuse connections within job context
  - Use context manager for connection lifecycle
- **Priority**: 🟡 MEDIUM

---

## 🟡 CODE QUALITY ISSUES

### 21. Broad Exception Handling
- **Issue**: 52 instances of generic `except:` or `except Exception:` without handling
- **Files**: Throughout `leads_scrapping.py`, `sheets_utils.py`, `main.py`
- **Examples**:
  ```python
  except: pass  # masks all errors
  except Exception as e:  # too generic
  ```
- **Impact**:
  - Masks real errors
  - Makes debugging impossible
  - Silent failures
- **Fix**:
  - Catch specific exceptions only
  - Log all exceptions with stack traces
  - Implement proper error recovery
  - Add error codes/types to distinguish issues
- **Priority**: 🟡 MEDIUM

### 22. Debug Prints in Production
- **Issue**: Debug print statements in production code
- **Files**: `selector_manager.py:42, 54, 60`
  ```python
  print(f"DEBUG: Loaded user selectors from {local_path}")
  ```
- **Impact**:
  - Clutters logs
  - Exposes internals
  - Can't be disabled without code changes
- **Fix**:
  - Use `logging.debug()` instead of `print()`
  - Add log level configuration
  - Remove or gate all DEBUG prints
- **Priority**: 🟡 MEDIUM

### 23. No Environment Variable Support
- **Issue**: Hardcoded paths, no `.env` file support
- **Hardcoded Paths**:
  - `"credentials.json"`
  - `"config.json"`
  - `"GMaps Data"`
- **Impact**: Hard to configure in different environments
- **Fix**:
  - Add `python-dotenv` dependency
  - Support environment variable overrides
  - Create `.env.example` file
  - Document all available env vars
- **Priority**: 🟡 MEDIUM

### 24. Missing Type Hints
- **Issue**: No type annotations on function signatures
- **Impact**:
  - Makes refactoring error-prone
  - No IDE autocomplete
  - Hard to understand expected types
- **Fix**:
  - Add type hints to all functions
  - Use `mypy` for type checking
  - Document complex types with docstrings
- **Priority**: 🟡 MEDIUM

### 25. Inadequate Logging
- **Issue**: Mix of `print()` and `logging` module, no log levels
- **Files**: Throughout codebase
- **Problems**:
  - No structured logging
  - No log rotation (except in logger.py)
  - Inconsistent format
  - Mix of debug/info/error messages
- **Fix**:
  - Standardize on `logging` module
  - Use proper log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Add structured logging with JSON format option
  - Add log filtering by module
- **Priority**: 🟡 MEDIUM

### 26. No Input Validation
- **Issue**: Config values not validated
- **Code**: `config_manager.py:50-51`
  ```python
  def get(self, key, default=None):
      return self.config.get(key, default)  # No validation
  ```
- **Problems**:
  - `max_scroll_time` could be "abc" (should be int)
  - `max_results` could be 1,000,000+ (should be limited)
  - `headless` could be "yes" (should be boolean)
- **Impact**: Crashes, unexpected behavior, performance issues
- **Fix**:
  - Add validation schema
  - Type checking on config load
  - Range validation for numeric values
  - Enum validation for categorical values
- **Priority**: 🟡 MEDIUM

### 27. Race Conditions
- **Issue**: File lock may not be cleaned on crash, potential deadlocks
- **Code**: `sheets_utils.py:146-183`
  ```python
  class FileLock:
      # Simple lock without proper cleanup
  ```
- **Problems**:
  - Lock file not cleaned if process crashes
  - No timeout on acquisition (infinite wait)
  - Deadlock if another process crashes holding lock
- **Impact**: Data corruption, hanging processes
- **Fix**:
  - Use `fcntl.fcntl` with timeout
  - Add lock cleanup in `__exit__`
  - Add PID tracking
  - Implement stale lock detection
  - Use `fcntl.LOCK_EX | fcntl.LOCK_NB`
- **Priority**: 🟡 MEDIUM

### 28. No Input Constraints
- **Issue**: No limits on user inputs
- **Examples**:
  - `max_results` could be 1,000,000+
  - Search queries have no length limit
  - No validation of query format
- **Impact**:
  - Performance issues
  - Memory exhaustion
  - API quota exceeded
- **Fix**:
  - Add max_results limit (e.g., 10,000 per query)
  - Limit query length (e.g., 500 chars)
  - Add query format validation
  - Rate limit based on result count
- **Priority**: 🟡 MEDIUM

---

## 🟢 MINOR ISSUES

### 29. Inconsistent Naming
- **Issues**:
  - `leads_scrapping.py` vs `leads_scraping.py` (typo in filename)
  - `db.py` vs database naming
  - Mixed snake_case and camelCase
- **Impact**: Confusing for contributors
- **Fix**: Standardize naming conventions
- **Priority**: 🟢 LOW

### 30. Unused Imports
- **Issue**: Import modules not used in code
- **Examples**:
  - `openpyxl` in requirements.txt but not used
  - Various unused imports in multiple files
- **Impact**: Larger bundle size, confusion
- **Fix**: Remove unused imports, audit with `flake8`
- **Priority**: 🟢 LOW

### 31. No Error Recovery
- **Issue**: If Sheets API fails, entire batch lost
- **Code**: `main.py:314-315`, `main_gui_wrapper.py:166-168`
  ```python
  except Exception as e:
      print(f"Failed to upload: {e}")
      # Data lost!
  ```
- **Impact**: Lost data, poor reliability
- **Fix**:
  - Add retry logic with exponential backoff
  - Queue failed uploads for retry
  - Persist failed data locally
  - Add retry queue management
- **Priority**: 🟢 LOW

### 32. No Data Validation
- **Issue**: Extracted data not validated
- **Problems**:
  - Phone numbers could be any format
  - URLs not validated
  - Emails not validated
  - Coordinates could be invalid
- **Impact**: Bad data in exports
- **Fix**:
  - Add validators for phone numbers
  - Validate URLs with regex
  - Validate coordinate ranges
  - Add data quality score
- **Priority**: 🟢 LOW

### 33. Missing Indexes
- **Issue**: Only indexes `name`, not `unique_key` (used for dedup)
- **Code**: `db.py:46`
  ```python
  conn.execute('CREATE INDEX IF NOT EXISTS idx_name ON leads(name)')
  ```
- **Impact**: Slow deduplication queries
- **Fix**:
  - Add index on `unique_key`
  - Add composite index on `(name, phone_number)`
  - Analyze query patterns and optimize indexes
- **Priority**: 🟢 LOW

### 34. Outdated Dependencies
- **Issue**: No pinned versions in requirements.txt (except pandas)
- **Impact**:
  - Security vulnerabilities possible
  - Breaking changes with auto-updates
  - Non-reproducible builds
- **Fix**:
  - Pin all package versions
  - Run `pip-audit` regularly
  - Add `requirements.lock` file
  - Implement security scanning in CI
- **Priority**: 🟢 LOW

### 35. No Tests for Critical Paths
- **Issue**: `test_scraper_basic.py` only tests basic navigation
- **Missing Tests**:
  - Deduplication logic
  - Database operations
  - Sheets sync
  - Config validation
  - Error handling
  - Controller signals
  - File locking
- **Impact**: Regression bugs, unreliable code
- **Fix**:
  - Add comprehensive test suite
  - Test all critical paths
  - Add integration tests
  - Test error scenarios
- **Priority**: 🟢 LOW

### 36. Memory Leaks
- **Issue**: Browser contexts not properly closed, large DataFrames held in memory
- **Problems**:
  - No explicit cleanup of browser contexts
  - DataFrames not cleared after use
  - No memory monitoring
- **Impact**: Memory exhaustion over time
- **Fix**:
  - Explicit cleanup in finally blocks
  - Use context managers for resources
  - Clear DataFrames after save
  - Add memory profiling
- **Priority**: 🟢 LOW

### 37. No Request Timeout Handling
- **Issue**: `page.goto()` can hang indefinitely
- **Files**: `main.py:251`, `leads_scrapping.py:95`
- **Impact**: Hanging scraper, unresponsive GUI
- **Fix**:
  - Add circuit breaker pattern
  - Implement timeout on all network requests
  - Add watchdog for hanging operations
  - Kill page after timeout
- **Priority**: 🟢 LOW

### 38. Broken CSV Export
- **Issue**: `save_to_csv()` ignores filename parameter
- **Code**: `main.py:304`
  ```python
  csv_path = business_list.save_to_csv(clean_filename)
  # But save_to_csv ignores filename parameter!
  ```
- **Code**: `sheets_utils.py:218-255`
  ```python
  def save_to_csv(self, filename) -> str:
      # FORCE filename to 'Gmaps Leads' regardless of input
      target_file = "Gmaps Leads"  # Ignores filename parameter!
  ```
- **Impact**: Cannot create separate CSV files per query
- **Fix**: Remove hardcoded filename override
- **Priority**: 🟢 LOW

### 39. Missing Retry Logic
- **Issue**: No retry mechanism for failed operations
- **Problems**:
  - No retry for Sheets API failures
  - No retry for DB connection errors
  - No retry for network timeouts
- **Impact**: Transient failures cause complete failure
- **Fix**:
  - Add retry decorator with exponential backoff
  - Configure max retries per operation type
  - Add jitter to retry delays
- **Priority**: 🟢 LOW

### 40. No Health Checks
- **Issue**: No monitoring of scraper health
- **Problems**:
  - No detection of memory leaks
  - No detection of stuck operations
  - No detection of error rate spikes
- **Impact**: Silent failures, poor reliability
- **Fix**:
  - Add health check endpoint/log
  - Monitor memory usage
  - Track error rates
  - Add auto-restart on failures
- **Priority**: 🟢 LOW

---

## 📊 PRIORITY FIX SUMMARY

### 🔴 IMMEDIATE (Security)
1. Remove/revoke exposed credentials
2. Add input validation & sanitization
3. Fix SQL injection risks
4. Add rate limiting with exponential backoff

### 🟠 HIGH (Functionality)
5. Fix duplicate browser launch (`main.py:234`)
6. Fix duplicate page goto (`main.py:253`)
7. Remove dead code (`sheets_utils.py:604`)
8. Fix undefined variable (`leads_scrapping.py:320`)
9. Validate resume functionality (`job_manager.py`)
10. Fix controller signal handling
11. **NEW**: Implement comprehensive diagnostics system with test selection
12. **NEW**: Add scrolling configuration to GUI
13. **NEW**: Add feature toggles to GUI

### 🟡 MEDIUM (Performance & Quality)
14. Cache database queries (N+1 problem)
15. Optimize deduplication (batch operations)
16. Implement smart scrolling (element detection)
17. Fix memory inefficiency (streaming/chunking)
18. Use consistent User-Agent
19. Implement connection pooling
20. Replace broad exception handling with specific catches
21. Remove debug prints, use logging module
22. Add environment variable support
23. Add type hints
24. Improve logging system
25. Add config validation
26. Fix file locking race conditions
27. Add input constraints

### 🟢 LOW (Quality & Maintenance)
28. Fix inconsistent naming
29. Remove unused imports
30. Add error recovery & retry logic
31. Add data validation
32. Add missing database indexes
33. Pin dependency versions
34. Add comprehensive test suite
35. Fix memory leaks
36. Add timeout handling
37. Fix CSV export filename issue
38. Add health monitoring

---

## 📝 IMPLEMENTATION NOTES

### Files Requiring Major Changes:
- `gui_app.py` - Diagnostics, scrolling config, feature toggles
- `src/config_manager.py` - New config keys, validation
- `src/leads_scrapping.py` - Scroll parameters, smart wait
- `main_gui_wrapper.py` - Pass new settings
- `main.py` - Fix bugs (lines 234, 253)
- `src/sheets_utils.py` - Remove dead code (line 604)
- `src/db.py` - Add indexes, connection pooling

### Files to Create:
- `test/test_config.py` - Config validation tests
- `test/test_headless_scrape.py` - Headless scraping test
- `test/test_headed_scrape.py` - Headed scraping test
- `test/test_data_extraction.py` - Data extraction tests
- `.env.example` - Environment variable template

### Dependencies to Add:
- `python-dotenv` - Environment variable support
- `tenacity` - Retry logic with exponential backoff
- `mypy` - Type checking
- `flake8` - Code quality checks
- `pip-audit` - Security vulnerability scanning

---

## 🔍 CURRENT STATISTICS

- **Total Issues**: 40
- **Security Issues**: 4
- **Critical Bugs**: 5
- **High Priority**: 9
- **Medium Priority**: 14
- **Low Priority**: 8
- **Estimated Fix Time**: 40-60 hours

---

*Last Updated: 2026-01-17*
*Total Lines of Code Analyzed: ~2,500*
*Issues Found: 40*