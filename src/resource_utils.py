import sys
import os

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_app_data_path(app_name="GoogleMapsScraper"):
    """ Get persistent data path in AppData/Local """
    app_data = os.getenv('LOCALAPPDATA')
    if not app_data:
        app_data = os.path.expanduser("~") # Fallback to user home
        
    path = os.path.join(app_data, app_name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_browsers_path():
    """ Get specific path for Playwright browsers """
    return os.path.join(get_app_data_path(), 'browsers')
