import threading
import time

class ScraperController:
    """
    Thread-safe controller for managing the scraper's execution state.
    """
    def __init__(self):
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._skip_event = threading.Event()
        self._pause_event.set()  # Set to True immediately so it starts NOT paused (Running)

    def stop(self):
        """Signal the scraper to stop completely."""
        self._stop_event.set()

    def pause(self):
        """Signal the scraper to pause execution."""
        self._pause_event.clear()

    def resume(self):
        """Signal the scraper to resume execution."""
        self._pause_event.set()
    
    def skip(self):
        """Signal to skip the current item."""
        self._skip_event.set()

    def is_stopped(self):
        """Check if stop has been requested."""
        return self._stop_event.is_set()

    def is_paused(self):
        """Check if currently paused."""
        return not self._pause_event.is_set()
    
    def is_skipped(self):
        """Check if skip has been requested."""
        if self._skip_event.is_set():
            self._skip_event.clear() # Auto-reset
            return True
        return False

    def check_pause(self):
        """
        Blocks execution if paused.
        Returns immediately if running.
        """
        self._pause_event.wait()
