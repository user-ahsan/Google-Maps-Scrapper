# Google Maps Scraper

A robust, production-ready Python tool for scraping business data from Google Maps. This scraper supports specialized queries, duplicate detection, and automated data export to CSV and Excel formats. It is designed to run indefinitely if needed, making it suitable for long-running data collection tasks.

## 🚀 Features

- **Multi-format Export**: Automatically saves data to both `.csv` and `.xlsx` files.
- **Duplicate Detection**: Smart hashing prevents duplicate entries based on business name and contact info.
- **Resilient**: Handles network timeouts and loading states automatically.
- **Configurable**: Run with command-line arguments or using a bulk input file.
- **Cross-Platform**: Fully compatible with Linux, Windows, WSL, and macOS.

---

## 📋 Prerequisites

- **Python 3.8+** must be installed on your system.
- **Google Chrome** (optional, but recommended for visual debugging).

---

## 🛠️ Installation Guide

Choose the instructions that match your operating system.

### Option A: Linux / macOS / Windows WSL (Ubuntu)

1.  **Open your terminal** (Terminal, iTerm, or WSL Console).
2.  **Navigate to the project folder:**
    ```bash
    cd /path/to/Googles-Maps-Scraper-master
    ```
3.  **Set up the Virtual Environment:**
    ```bash
    # Create virtual environment
    python3 -m venv venv

    # Activate it
    source venv/bin/activate
    ```
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Install Playwright Browsers:**
    ```bash
    playwright install chromium
    ```

### Option B: Windows (Native PowerShell/CMD)

1.  **Open Command Prompt (cmd) or PowerShell**.
2.  **Navigate to the project folder:**
    ```cmd
    cd C:\path\to\Googles-Maps-Scraper-master
    ```
3.  **Set up the Virtual Environment:**
    ```cmd
    :: Create virtual environment
    python -m venv venv

    :: Activate it
    venv\Scripts\activate
    ```
4.  **Install Dependencies:**
    ```cmd
    pip install -r requirements.txt
    ```
5.  **Install Playwright Browsers:**
    ```cmd
    playwright install chromium
    ```

---

## ⚙️ Configuration

### Bulk Search (Recommended)
Edit the `input.txt` file in the root directory. Add one search query per line.

**Example `input.txt`:**
```text
retail store in riyadh
coffee shops in jeddah
restaurants in london
```

### Command Line Arguments
You can also pass arguments directly to the script:
- `-s "search query"`: Specific search term (overrides `input.txt`).
- `-t 100`: Total number of results to scrape per query (default: 1,000,000).
- `-headed`: See the browser window while scraping (useful for debugging).

---

## 🏃 usage

### 1. Standard Run
Runs through the queries in `input.txt` once and exits.

**Linux / macOS / WSL:**
```bash
source venv/bin/activate
python main.py
```

**Windows:**
```cmd
venv\Scripts\activate
python main.py
```

### 2. Infinite Loop Mode (Production)
Use this mode to keep the scraper running continuously. If it crashes or finishes all tasks, it will automatically restart after a short delay.

**Linux / macOS / WSL:**
Make the script executable (first time only) and run it:
```bash
chmod +x run_forever.sh
./run_forever.sh
```

**Windows:**
Double-click `run_forever.bat` or run it from the command line:
```cmd
run_forever.bat
```

### 3. Visual Debugging
To watch the bot work (useful if you suspect Google is blocking requests or layout has changed):

```bash
python main.py -headed
```

---

## 📂 Output

Data is saved automatically in the `GMaps Data` folder, organized by date.

**Directory Structure:**
```text
Googles-Maps-Scraper-master/
├── GMaps Data/
│   ├── 2025-12-25/
│   │   ├── retail_store_in_riyadh.csv
│   │   └── retail_store_in_riyadh.xlsx
│   └── 2025-12-27/
│       ├── ...
```

---

## ❓ Troubleshooting

**Q: `ModuleNotFoundError: No module named ...`**
A: Ensure your virtual environment is activated (`source venv/bin/activate` or `venv\Scripts\activate`) and you have run `pip install -r requirements.txt`.

**Q: The scraper opens the browser but immediately closes.**
A: Pass the `-headed` flag to see if an error message appears on the screen.

**Q: "Access Denied" or Permission errors.**
A: Ensure you have read/write permissions for the project directory. On Linux/Mac, try `chmod +x run_forever.sh`.

**Q: Does this run on WSL1 or WSL2?**
A: Both work, but WSL2 is recommended for better performance. If using WSL1, you might strictly need the headless mode.