import json
import os
import sys

from .logger import setup_logger

logger = setup_logger(__name__)

class SelectorManager:
    """
    Manages loading of CSS/XPath selectors from an external JSON file.
    Prioritizes:
    1. User 'assets/selectors.json' (cwd)
    2. Bundled 'assets/selectors.json' (_MEIPASS)
    3. Hardcoded defaults (Fallback)
    """

    _defaults = {
        "search_box": [
            "input[name=\"q\"]",
            "input#searchboxinput",
            "input#searchbox-input",
            "input[aria-label=\"Search Google Maps\"]",
            "input[role=\"combobox\"]",
            "input.searchboxinput"
        ],
        "feed": "div[role=\"feed\"]",
        "listings": "//a[contains(@href, \"https://www.google.com/maps/place\")]",
        "details_pane": "div[role=\"main\"]",
        "business_name": "h1",
        "address_button": "button[data-item-id=\"address\"]",
        "website_link": "a[data-item-id=\"authority\"]",
        "phone_button": "button[data-item-id*=\"phone:tel:\"]",
        "category_button": [
            "button[jsaction*=\"category\"]",
            "button[aria-label*=\"Categories\"]",
            "[data-item-id=\"category\"]",
            "span.DkEaL"
        ],
        "stars_aria": "span[role=\"img\"][aria-label*=\"stars\"]",
        "reviews_button": "div[role=\"button\"][aria-label*=\"reviews\"]",
        "reviews_generic": "[aria-label*=\"reviews\"]"
    }

    def __init__(self):
        self.selectors = self._load_selectors()

    def _load_selectors(self):
        # 1. Check CWD (User overrides)
        local_path = os.path.join(os.getcwd(), 'assets', 'selectors.json')
        if os.path.exists(local_path):
            try:
                with open(local_path) as f:
                    logger.debug(f"Loaded user selectors from {local_path}")
                    return self._merge_defaults(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load user selectors: {e}")

        # 2. Check Bundled (PyInstaller)
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path:
            bundled_path = os.path.join(base_path, 'assets', 'selectors.json')
            if os.path.exists(bundled_path):
                try:
                    with open(bundled_path) as f:
                        logger.debug(f"Loaded bundled selectors from {bundled_path}")
                        return self._merge_defaults(json.load(f))
                except Exception as e:
                    logger.warning(f"Failed to load bundled selectors: {e}")

        # 3. Fallback
        logger.debug("Using hardcoded default selectors")
        return self._defaults

    def _merge_defaults(self, loaded):
        """Ensure all keys exist even if file is partial"""
        merged = self._defaults.copy()
        merged.update(loaded)
        return merged

    def get(self, key):
        return self.selectors.get(key, self._defaults.get(key))
