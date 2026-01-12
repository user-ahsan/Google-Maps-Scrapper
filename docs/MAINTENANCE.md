# Maintenance Guide

This guide explains how to maintain the Google Maps Scraper, specifically how to handle Google UI updates and debug issues using the new hardening features.

## 1. Updating Selectors (Fixing Broken Scrapers)

The scraper relies on **Selectors** (Css/XPath) to find elements on the Google Maps page. If Google changes their website layout, the scraper might stop working (e.g., "Could not find search box" or "Failed to extract Name").

**You do NOT need to rebuild the executable to fix this.**

### How to Update
1.  Navigate to the `assets/` folder next to your script or executable.
2.  Open `selectors.json` in any text editor (Notepad, VS Code).
3.  Locate the failing key (e.g., `search_box`, `business_name`).
4.  Update the value with the new valid CSS selector or XPath.
    -   *Tip: Use your browser's Developer Tools (F12) -> Inspect Element to find the new class or ID.*
5.  Save the file.
6.  Restart the scraper. It will automatically load the new selectors.

### Selector Keys Reference
| Key | Description |
| :--- | :--- |
| `search_box` | List of selectors to find the main search input field. |
| `listings` | The selector for individual business cards in the scroll list. |
| `business_name` | The element containing the business name in the details pane (usually `h1`). |
| `phone_button` | Button or element containing the phone number. |
| `reviews_generic` | Used to find review counts if the primary method fails. |

## 2. Debugging with Logs

If the application crashes or behaves unexpectedly, check the log file.

**Log Location:**
`%LOCALAPPDATA%\GoogleMapsScraper\scraper.log`
*(Paste this path into your Windows File Explorer address bar)*

### What to look for
-   **CRITICAL**: Fatal errors that stopped the script.
-   **ERROR**: Issues with specific listings (e.g., "Could not locate business details").
-   **INFO**: General progress (e.g., "Start Scraping...", "Browsers Installed").

## 3. Rebuilding the Executable

If you modify the Python code (files in `src/` or `gui_app.py`), you must rebuild the EXE.

1.  Activate your virtual environment.
2.  Run:
    ```cmd
    pyinstaller scraper.spec
    ```
3.  The new `GoogleMapsScraper.exe` will be in the `dist/` folder.
