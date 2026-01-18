# Configuration & Security (`src/config_manager.py`, `src/security_utils.py`)

## 📝 Overview
These modules handle the **safety** and **state** of the application. They ensure user inputs are valid, secrets are handled correctly, and settings persist across restarts.

## ⚙️ Config Manager (`src/config_manager.py`)

### `ConfigManager` Class
-   **Storage**: Reads/Writes to `config.json` in the root directory.
-   **Validation**: When loading, it checks if values are sane (e.g., `max_results` > 0). If the file is corrupted, it loads a safe `DEFAULT_CONFIG`.
-   **Keys Managed**:
    -   `max_results`: Limit on leads per query.
    -   `headless`: Boolean for browser visibility.
    -   `search_queries`: List of saved past queries.

## 🛡️ Security Utils (`src/security_utils.py`)

### `validate_input(type, value)`
Prevents injection attacks and ensures data quality.
-   **Regex Checks**: specific patterns for filenames (no `..`, no slashes) and search queries (limiting special chars).
-   **Why?**: Since we save files based on search queries (`"Query.csv"`), a malicious query like `../../windows/system32` could be dangerous. This util blocks that.

### `safe_file_path(path)`
-   Ensures that any file operation stays within the project directory.
-   Uses `os.path.abspath` and comparisons to prevent **Directory Traversal** attacks.

### `clean_text(input)`
-   Removes control characters, BOMs, and weird unicode that might break CSV parsers or the console.
