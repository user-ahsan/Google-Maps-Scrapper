import json
import os

class ConfigManager:
    """
    Manages persistent application settings using a JSON file.
    Default configuration ensures safe initial values.
    """
    DEFAULT_CONFIG = {
        "input_file": "",
        "creds_file": "credentials.json",
        "max_results": "100",
        "headless": True,
        "sheet_behavior": "Append",  # Options: Append, Overwrite, New Sheet
        "max_scroll_time": "300",     # Seconds
        "max_scroll_retries": "5",
        "theme": "Dark"
    }

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        """Load config from file, or return defaults if missing/corrupt."""
        if not os.path.exists(self.config_file):
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                # Merge with defaults to ensure all keys exist
                new_config = self.DEFAULT_CONFIG.copy()
                new_config.update(data)
                return new_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.DEFAULT_CONFIG.copy()

    def save_config(self, data):
        """Save current configuration to file."""
        self.config.update(data)
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
        self.save_config({}) # Auto-save on set? Or manual? Let's auto-save for simplicity in GUI.
        # Actually safer to just update memory and let caller convert to dict for save_config if bulk update needed.
        # But for single property, auto-save is nice.
        self._save_to_disk()

    def _save_to_disk(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
