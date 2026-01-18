# GUI application Architecture (`gui_app.py`, `controller.py`, `job_manager.py`)

## 📝 Overview
The GUI is built using `customtkinter`, a modern wrapper around Python's standard `tkinter`. It follows a **Model-View-Controller (MVC)**-like pattern to keep the UI responsive while the heavy scraping runs in the background.

## 🧩 Components

### 1. The View: `gui_app.py`
-   **Role**: Draws the window, buttons, inputs, and log console.
-   **Threading**: It has a `queue.Queue` for logs. The UI thread reads from this queue every 100ms (`after` loop) to update the console text without freezing.
-   **Inputs**: Binds variables (`ctk.StringVar`) to `config.json` settings via `ConfigManager`.

### 2. The Bridge: `controller.py`
-   **Role**: Decouples the UI from the logic.
-   **Action**: When "Start Scrape" is clicked:
    1.  Controller validates inputs.
    2.  Controller initializes the `JobManager`.
    3.  Controller spawns a **new thread** (`threading.Thread`) targeting `main_gui_wrapper.py`.

### 3. The Worker: `job_manager.py`
-   **Role**: Controls the execution state.
-   **Flags**:
    -   `pause_event` (threading.Event): If clear, the scraper loop waits (sleeping).
    -   `stop_event` (threading.Event): If set, the scraper loop breaks and cleans up.
-   **Usage**: The scraping engine in `leads_scraping.py` periodically checks `job_manager.should_continue()` to respect user clicks.

## 🔄 Data Flow
1.  **User** types "Plumbers" -> Clicks Start.
2.  **View** passes string to **Controller**.
3.  **Controller** saves `config.json` and starts **Thread**.
4.  **Thread** runs `run_scraping_logic`.
5.  **Scraper** emits logs -> **Queue** -> **View** displays log.
6.  **Scraper** finds lead -> Saves to DB/Sheet directly (Back-end).
