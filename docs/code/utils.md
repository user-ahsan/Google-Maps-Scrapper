# Utilities Documentation (`src/logger.py`, `src/resource_utils.py`, `src/selector_manager.py`)

## 📝 Overview
These are helper modules that support the main application infrastructure.

## 🪵 Logger (`src/logger.py`)
Centralized logging configuration.
-   **Function**: `setup_logger(name)`
-   **Output**: 
    -   Console (StreamHandler)
    -   File (`debug.log` in root)
-   **Formatting**: Includes timestamps and log levels (INFO, ERROR, DEBUG).

## 📦 Resource Utils (`src/resource_utils.py`)
Handles file paths for assets, especially when the application is bundled as an executable.
-   **Problem**: PyInstaller unpacks files to a temporary `_MEIxxxx` directory at runtime. Standard relative paths (`./assets/icon.ico`) fail.
-   **Solution**: `resource_path(relative_path)` checks `sys._MEIPASS` to look in the temporary folder if running as an `.exe`.

## 🎯 Selector Manager (`src/selector_manager.py`)
(Optional/Advanced)
-   **Purpose**: Decouples CSS/XPath selectors from the Python code.
-   **Usage**: Can load a JSON file (`selector_db.json`) containing mappings like `{"business_name": "//div[@class='...']"}`.
-   **Benefit**: Allows fixing broken scrapers by updating a JSON file instead of recompiling the code.
