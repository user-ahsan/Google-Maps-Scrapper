---
trigger: always_on
glob: overall
description: # AI Agent Rules for Google Maps Scraper

These rules must be strictly followed by any AI agent working on this repository to ensure data integrity and scraper reliability.

## 1. PRESERVE EXTRACTION SELECTORS

* **DO NOT check or modify XPath or CSS selectors** (e.g., `h1.DUwDvf`, `span[role="img"]`, `div[role="feed"]`) unless you have explicit confirmation that Google's DOM has changed.

- **Why**: These selectors are fragile and specific to the current DOM layout. "Cleaning" them often breaks extraction.
- **Action**: If you suspect a selector is broken, verify it with a dry-run test before committing changes.

## 2. PROTECT THE SCROLL & SCRAPE LOGIC

**DO NOT refactor the core `while True` loop** in `scrape_data` or the list collection logic.

- **Why**: The specific timing, scroll increments, and "end of list" checks (`MAX_NO_CHANGE`) are tuned to avoid bot detection and ensure all items load.
- **Action**: Treat the structural flow of `leads_scrapping.py` as read-only unless the task is specifically to fix a logic bug.

## 3. NO AESTHETIC-ONLY REFACTORS ON LOGIC

**DO NOT apply "clean code" or formatting refactors** to `leads_scrapping.py` that alter control flow (e.g., extracting methods, changing variable names like `details_pane`) without testing.

- **Why**: The script relies on specific variable scopes and fallback logic (e.g., trying `details_pane` then falling back to `page`). Refactoring can obscure or break these safety nets.
- **Action**: Only refactor if it objectively fixes a bug or adds requested functionality.

## 4. MANDATORY VERIFICATION

**ALWAYS verify data output** after touching any part of `src/`.

- **Why**: Small changes can silently result in empty fields (e.g., 0 reviews, missing phones).
- **Action**: Run a short search (e.g., `-s "bars in london" -t 5`) and check the CSV output to ensure Name, Phone, and Review Count are populated before finishing the task.
---
