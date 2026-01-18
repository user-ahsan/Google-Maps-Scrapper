import json
import os

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    def load_dotenv():
        pass

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
        "max_scroll_time": "300",       # Seconds
        "max_scroll_retries": "5",
        "scroll_wait": "3000",           # Milliseconds between scrolls
        "scroll_amount_per_step": "10000", # Pixels to scroll per step
        "auto_skip_timeout": "0",         # Seconds (0 = disabled)
        "smart_wait_enabled": True,        # Use smart element detection
        "use_feed_scroll": True,           # Use feed scroll vs global scroll
        "theme": "Dark",
        "user_agent": "",  # Empty = auto-generate, otherwise use stored value
        "export_csv": True,            # Export data to CSV files
        "export_sheets": True,          # Export to Google Sheets
        "export_db": True,               # Export to SQLite database
        "auto_upload": False,            # Auto-upload on complete
        "auto_accept": True,              # Auto-accept URLs
        "manual_verification": False,     # Manual verification prompt
        "interactive_controls": True,     # Enable interactive controls
        "show_progress": True,            # Show progress bars
        "pre_filter_names": True,         # Pre-filter by known names
        "batch_db_ops": True,            # Batch database operations
        "cache_sheet_data": True,         # Cache sheet data
    }

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self._load_env_file()
        self.config = self.load_config()
    
    def _load_env_file(self):
        if not DOTENV_AVAILABLE:
            return
            
        env_files = ['.env', '.env.local', '.env.example']
        for env_file in env_files:
            if os.path.exists(env_file):
                load_dotenv()
                print(f"Loaded environment variables from {env_file}")
                break

    def load_config(self):
        """Load config from file and environment variables, or return defaults if missing/corrupt."""
        if not os.path.exists(self.config_file):
            config = self.DEFAULT_CONFIG.copy()
        else:
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(data)
            except Exception as e:
                print(f"Error loading config: {e}")
                config = self.DEFAULT_CONFIG.copy()
        
        # Override with environment variables if present
        # Env vars should match config keys with GMS_ prefix
        env_mapping = {
            'GMS_INPUT_FILE': 'input_file',
            'GMS_CREDS_FILE': 'creds_file',
            'GMS_MAX_RESULTS': 'max_results',
            'GMS_HEADLESS': 'headless',
            'GMS_SHEET_BEHAVIOR': 'sheet_behavior',
            'GMS_MAX_SCROLL_TIME': 'max_scroll_time',
            'GMS_MAX_SCROLL_RETRIES': 'max_scroll_retries',
            'GMS_SCROLL_WAIT': 'scroll_wait',
            'GMS_SCROLL_AMOUNT_PER_STEP': 'scroll_amount_per_step',
            'GMS_AUTO_SKIP_TIMEOUT': 'auto_skip_timeout',
            'GMS_SMART_WAIT_ENABLED': 'smart_wait_enabled',
            'GMS_USE_FEED_SCROLL': 'use_feed_scroll',
            'GMS_THEME': 'theme',
            'GMS_EXPORT_CSV': 'export_csv',
            'GMS_EXPORT_SHEETS': 'export_sheets',
            'GMS_EXPORT_DB': 'export_db',
            'GMS_AUTO_UPLOAD': 'auto_upload',
            'GMS_AUTO_ACCEPT': 'auto_accept',
            'GMS_MANUAL_VERIFICATION': 'manual_verification',
            'GMS_INTERACTIVE_CONTROLS': 'interactive_controls',
            'GMS_SHOW_PROGRESS': 'show_progress',
            'GMS_PRE_FILTER_NAMES': 'pre_filter_names',
            'GMS_BATCH_DB_OPS': 'batch_db_ops',
            'GMS_CACHE_SHEET_DATA': 'cache_sheet_data',
        }
        
        for env_var, config_key in env_mapping.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Convert to appropriate type
                default_value = self.DEFAULT_CONFIG.get(config_key)
                if isinstance(default_value, bool):
                    env_value = env_value.lower() in ('true', '1', 'yes')
                elif isinstance(default_value, int):
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        continue
                config[config_key] = env_value
        
        return config

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
