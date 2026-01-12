import logging
import os
from logging.handlers import RotatingFileHandler
from .resource_utils import get_app_data_path

def setup_logger(name="ScraperLogger"):
    """
    Sets up a file-based logger in AppData.
    """
    log_dir = get_app_data_path()
    log_file = os.path.join(log_dir, 'scraper.log')

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Check if handlers already exist to avoid duplicate logs
    if not logger.handlers:
        # File Handler (Rotating)
        # Max 5MB, keep 1 backup
        try:
            file_handler = RotatingFileHandler(
                log_file, maxBytes=5*1024*1024, backupCount=1, encoding='utf-8'
            )
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"FAILED TO SETUP LOGGING: {e}")

    return logger
