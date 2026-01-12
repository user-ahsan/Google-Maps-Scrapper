import json
import os
import sys

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
            "input[aria-label=\"Search Google Maps\"]"
        ],
        "feed": "div[role=\"feed\"]",
        "listings": "//a[contains(@href, \"https://www.google.com/maps/place\")]",
        "details_pane": "div[role=\"main\"]",
        "business_name": "h1",
        "address_button": "button[data-item-id=\"address\"]",
        "website_link": "a[data-item-id=\"authority\"]",
        "phone_button": "button[data-item-id*=\"phone:tel:\"]",
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
                with open(local_path, 'r') as f:
                    print(f"DEBUG: Loaded user selectors from {local_path}")
                    return self._merge_defaults(json.load(f))
            except Exception as e:
                print(f"WARNING: Failed to load user selectors: {e}")

        # 2. Check Bundled (PyInstaller)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            bundled_path = os.path.join(base_path, 'assets', 'selectors.json')
            if os.path.exists(bundled_path):
                try:
                    with open(bundled_path, 'r') as f:
                        print(f"DEBUG: Loaded bundled selectors from {bundled_path}")
                        return self._merge_defaults(json.load(f))
                except Exception as e:
                    print(f"WARNING: Failed to load bundled selectors: {e}")
        
        # 3. Fallback
        print("DEBUG: Using hardcoded default selectors")
        return self._defaults

    def _merge_defaults(self, loaded):
        """Ensure all keys exist even if file is partial"""
        merged = self._defaults.copy()
        merged.update(loaded)
        return merged

    def get(self, key):
        return self.selectors.get(key, self._defaults.get(key))
