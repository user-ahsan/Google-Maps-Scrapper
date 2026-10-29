import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Dict, List

import customtkinter as ctk

import main_gui_wrapper
from src import resource_utils
from src.config_manager import ConfigManager
from src.controller import ScraperController
from src.job_manager import JobManager
from src.logger import setup_logger
from src.security_utils import validate_input

# --- THEME SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- CONSTANTS ---
PLAYWRIGHT_BROWSERS_PATH = resource_utils.get_browsers_path()
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_BROWSERS_PATH


class TextRedirector:
    """Redirects stdout/stderr to a queue for the GUI to consume."""

    def __init__(self, widget_queue: queue.Queue, tag: str = "stdout") -> None:
        self.widget_queue = widget_queue
        self.tag = tag
        self.encoding = "utf-8"

    def write(self, str_val: str) -> None:
        ignored_patterns = (
            "Exception ignored while calling deallocator",
            "RuntimeError: main thread is not in main loop",
            "Variable.__del__",
        )
        if any(pat in str_val for pat in ignored_patterns):
            return
        # Strip ANSI codes for clean logs
        clean_text = re.sub(r"\x1b\[[0-9;]*m", "", str_val)
        self.widget_queue.put(clean_text)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False


class ScraperGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        # --- CONFIGURATION ---
        self.config_manager = ConfigManager()
        self.config: Dict[str, Any] = self.config_manager.load_config()
        self.logger = setup_logger("GUILogger")
        self.job_manager = JobManager()

        # Window Config
        self.title("Google Maps Scraper Pro")
        self.geometry("1100x800")

        # State
        self.controller = ScraperController()
        self.log_queue: queue.Queue = queue.Queue()
        self.stats_queue: queue.Queue = queue.Queue()
        self.scraper_thread: threading.Thread | None = None
        self.active_frame: str | None = None

        # General Variables (explicit master=self to prevent deallocator race conditions)
        self.input_file_path = ctk.StringVar(master=self, value=self.config.get("input_file", ""))
        self.creds_file_path = ctk.StringVar(master=self, value=self.config.get("creds_file", "credentials.json"))
        self.max_results_var = ctk.StringVar(master=self, value=str(self.config.get("max_results", "100")))
        self.headless_var = ctk.BooleanVar(master=self, value=bool(self.config.get("headless", True)))
        self.csv_export_var = ctk.BooleanVar(master=self, value=bool(self.config.get("export_csv", True)))

        # Scrolling Configuration
        self.sheet_behavior_var = ctk.StringVar(master=self, value=self.config.get("sheet_behavior", "Append"))
        self.max_scroll_time_var = ctk.StringVar(master=self, value=str(self.config.get("max_scroll_time", "300")))
        self.scroll_wait_var = ctk.StringVar(master=self, value=str(self.config.get("scroll_wait", "3000")))
        self.scroll_amount_var = ctk.StringVar(
            master=self, value=str(self.config.get("scroll_amount_per_step", "10000"))
        )
        self.auto_skip_var = ctk.StringVar(master=self, value=str(self.config.get("auto_skip_timeout", "0")))
        self.smart_wait_var = ctk.BooleanVar(master=self, value=bool(self.config.get("smart_wait_enabled", True)))
        self.feed_scroll_var = ctk.BooleanVar(master=self, value=bool(self.config.get("use_feed_scroll", True)))
        self.max_retries_var = ctk.StringVar(master=self, value=str(self.config.get("max_scroll_retries", "5")))

        # Data Export Toggles
        self.sheets_export_var = ctk.BooleanVar(master=self, value=bool(self.config.get("export_sheets", True)))
        self.db_export_var = ctk.BooleanVar(master=self, value=bool(self.config.get("export_db", True)))
        self.auto_upload_var = ctk.BooleanVar(master=self, value=bool(self.config.get("auto_upload", False)))

        # Behavior Toggles
        self.auto_accept_var = ctk.BooleanVar(master=self, value=bool(self.config.get("auto_accept", True)))
        self.manual_verify_var = ctk.BooleanVar(master=self, value=bool(self.config.get("manual_verification", False)))
        self.interactive_var = ctk.BooleanVar(master=self, value=bool(self.config.get("interactive_controls", True)))
        self.show_progress_var = ctk.BooleanVar(master=self, value=bool(self.config.get("show_progress", True)))

        # Performance Toggles
        self.pre_filter_var = ctk.BooleanVar(master=self, value=bool(self.config.get("pre_filter_names", True)))
        self.batch_db_var = ctk.BooleanVar(master=self, value=bool(self.config.get("batch_db_ops", True)))
        self.cache_sheet_var = ctk.BooleanVar(master=self, value=bool(self.config.get("cache_sheet_data", True)))

        # --- LAYOUT CONSTRUCTION ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.create_sidebar()
        self.create_pages()

        # Initial View
        self.select_frame("Dashboard")

        # Poll for logs
        self.after(100, self.update_console)

        # Resume Check
        self.after(1000, self.check_resume_state)

    def create_sidebar(self) -> None:
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="GMap Scraper",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#FFFFFF",
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Nav Buttons
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        self.btn_dashboard = self.create_nav_button("📊 Dashboard", "Dashboard", 1)
        self.btn_scrape = self.create_nav_button("🕸️ New Scrape", "Scrape", 2)
        self.btn_settings = self.create_nav_button("⚙️ Settings", "Settings", 3)
        self.btn_logs = self.create_nav_button("📝 Logs", "Logs", 4)
        self.nav_buttons["Dashboard"] = self.btn_dashboard
        self.nav_buttons["Scrape"] = self.btn_scrape
        self.nav_buttons["Settings"] = self.btn_settings
        self.nav_buttons["Logs"] = self.btn_logs

        # Status / Controls (Bottom)
        self.controls_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.controls_frame.grid(row=6, column=0, padx=10, pady=20, sticky="ew")

        self.btn_stop = ctk.CTkButton(
            self.controls_frame,
            text="STOP JOB",
            fg_color="#FF4444",
            hover_color="#CC0000",
            state="disabled",
            command=self.stop_scraping,
        )
        self.btn_stop.pack(fill="x")

    def create_nav_button(self, text: str, value: str, row: int) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            fg_color="transparent",
            text_color=("gray90", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=lambda v=value: self.select_frame(v),
        )
        btn.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        return btn

    def create_pages(self) -> None:
        self.frames: Dict[str, Any] = {}

        self.frames["Dashboard"] = self.create_dashboard_frame()
        self.frames["Scrape"] = self.create_scrape_frame()
        self.frames["Settings"] = self.create_settings_frame()
        self.frames["Logs"] = self.create_logs_frame()

        for f in self.frames.values():
            f.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

    # --- PAGES ---

    def create_dashboard_frame(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        ctk.CTkLabel(f, text="Overview", font=("Arial", 28, "bold")).pack(pady=30, padx=40, anchor="w")

        stats_box = ctk.CTkFrame(f, fg_color="#333333", corner_radius=10)
        stats_box.pack(pady=10, padx=40, fill="x")

        # Stats Grid
        self.lbl_status = ctk.CTkLabel(stats_box, text="IDLE", font=("Arial", 20, "bold"), text_color="#2CC985")
        self.lbl_status.pack(side="left", padx=30, pady=20)

        ctk.CTkLabel(stats_box, text="|", font=("Arial", 20)).pack(side="left", padx=10)

        self.lbl_leads = ctk.CTkLabel(stats_box, text="Leads: 0", font=("Arial", 20))
        self.lbl_leads.pack(side="left", padx=30)

        return f

    def create_scrape_frame(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        ctk.CTkLabel(f, text="New Scraping Job", font=("Arial", 28, "bold")).pack(pady=30, padx=40, anchor="w")

        # Input Area
        ctk.CTkLabel(f, text="Enter Keywords (One per line):", font=("Arial", 14)).pack(padx=40, anchor="w")
        self.txt_input = ctk.CTkTextbox(f, width=600, height=200, font=("Consolas", 14))
        self.txt_input.pack(padx=40, pady=10, fill="x")

        # Actions
        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(padx=40, pady=20, fill="x")

        self.btn_start = ctk.CTkButton(
            btn_box,
            text="START SCRAPING",
            font=("Arial", 16, "bold"),
            height=50,
            fg_color="#2CC985",
            hover_color="#229966",
            command=self.start_scraping,
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_resume_ui = ctk.CTkButton(
            btn_box,
            text="RESUME PREVIOUS",
            font=("Arial", 16, "bold"),
            height=50,
            fg_color="#FFA500",
            hover_color="#CC8400",
            state="disabled",
            command=self.resume_scraping,
        )
        self.btn_resume_ui.pack(side="left", fill="x", expand=True, padx=(10, 0))

        return f

    def create_settings_frame(self) -> ctk.CTkScrollableFrame:
        f = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        ctk.CTkLabel(f, text="Settings", font=("Arial", 28, "bold")).pack(pady=30, padx=40, anchor="w")

        def add_section(title: str) -> None:
            ctk.CTkLabel(
                f, text=title, font=("Arial", 16, "bold"), text_color="#2CC985"
            ).pack(pady=(20, 10), padx=40, anchor="w")

        def add_field(label: str, var: tk.Variable) -> None:
            row = ctk.CTkFrame(f, fg_color="transparent")
            row.pack(fill="x", padx=40, pady=5)
            ctk.CTkLabel(row, text=label, width=150, anchor="w").pack(side="left")
            ctk.CTkEntry(row, textvariable=var, width=300).pack(side="left")

        def add_switch(label: str, var: tk.Variable) -> None:
            ctk.CTkSwitch(f, text=label, variable=var).pack(padx=40, pady=10, anchor="w")

        # General
        add_section("General Config")
        add_field("Max Results / Query:", self.max_results_var)
        add_switch("Headless Mode (Background)", self.headless_var)
        add_switch("Export to CSV Files", self.csv_export_var)

        # Files
        add_section("File Paths")
        r_creds = ctk.CTkFrame(f, fg_color="transparent")
        r_creds.pack(fill="x", padx=40, pady=5)
        ctk.CTkLabel(r_creds, text="Credentials JSON:", width=150, anchor="w").pack(side="left")
        ctk.CTkEntry(r_creds, textvariable=self.creds_file_path, width=220).pack(side="left")
        ctk.CTkButton(r_creds, text="Browse", width=70, command=self.browse_creds).pack(side="left", padx=10)

        # Scrolling Configuration
        add_section("Scrolling Configuration")
        add_field("Scroll Amount Per Step (pixels):", self.scroll_amount_var)
        add_field("Scroll Wait/Interval (ms):", self.scroll_wait_var)
        add_field("Max Scroll Time (s):", self.max_scroll_time_var)
        add_field("Auto-Skip Timeout (s, 0=disabled):", self.auto_skip_var)
        add_field("Max Retries (no change):", self.max_retries_var)
        add_switch("Smart Wait (element detection)", self.smart_wait_var)
        add_switch("Use Feed Scroll Mode", self.feed_scroll_var)

        # Sheet Behavior
        ctk.CTkLabel(f, text="Sheet Behavior:", width=150, anchor="w").pack(padx=40, pady=(10, 0), anchor="w")
        ctk.CTkOptionMenu(
            f, values=["Append", "Overwrite", "New Sheet"], variable=self.sheet_behavior_var
        ).pack(padx=40, pady=5, anchor="w")

        # Data Export Toggles
        add_section("Data Export Toggles")
        add_switch("Export to Google Sheets", self.sheets_export_var)
        add_switch("Export to SQLite Database", self.db_export_var)
        add_switch("Auto-upload on Complete", self.auto_upload_var)

        # Behavior Toggles
        add_section("Behavior Toggles")
        add_switch("Auto-accept URLs", self.auto_accept_var)
        add_switch("Manual Verification", self.manual_verify_var)
        add_switch("Interactive Controls", self.interactive_var)
        add_switch("Show Progress Bars", self.show_progress_var)

        # Performance Toggles
        add_section("Performance Toggles")
        add_switch("Pre-filter by Known Names", self.pre_filter_var)
        add_switch("Batch Database Operations", self.batch_db_var)
        add_switch("Cache Sheet Data", self.cache_sheet_var)

        # System Tools
        add_section("System Tools")
        ctk.CTkButton(
            f, text="Re-Install Browsers", command=self.install_browsers_gui, fg_color="#555555"
        ).pack(padx=40, pady=5, anchor="w")
        ctk.CTkButton(
            f, text="Run Diagnostics", command=self.run_diagnostics_gui, fg_color="#4444aa"
        ).pack(padx=40, pady=5, anchor="w")
        ctk.CTkButton(
            f, text="Open Data Folder", command=self.open_data_folder, fg_color="#333333"
        ).pack(padx=40, pady=5, anchor="w")

        # Save Button
        ctk.CTkButton(
            f, text="SAVE SETTINGS", command=self.save_settings, fg_color="#2CC985", height=40, font=("Arial", 14, "bold")
        ).pack(padx=40, pady=30, anchor="w", fill="x")

        return f

    def create_logs_frame(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        ctk.CTkLabel(f, text="System Logs", font=("Arial", 28, "bold")).pack(pady=30, padx=40, anchor="w")

        self.console_box = ctk.CTkTextbox(
            f, font=("Consolas", 12), text_color="#DDDDDD", fg_color="#111111", wrap="none"
        )
        self.console_box.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        self.console_box.configure(state="disabled")

        # Setup tags on underlying Tkinter widget
        tk_textbox = getattr(self.console_box, "_textbox", None)
        if tk_textbox:
            tk_textbox.tag_config("error", foreground="#FF4444")
            tk_textbox.tag_config("success", foreground="#00FF00")
            tk_textbox.tag_config("warning", foreground="#FFA500")

        return f

    # --- LOGIC ---

    def select_frame(self, name: str) -> None:
        self.active_frame = name
        for frame in self.frames.values():
            frame.grid_forget()
        self.frames[name].grid(row=0, column=1, sticky="nsew")

        if hasattr(self, "nav_buttons"):
            for nav_name, btn in self.nav_buttons.items():
                if nav_name == name:
                    btn.configure(fg_color=("gray75", "gray25"))
                else:
                    btn.configure(fg_color="transparent")

    def check_resume_state(self) -> None:
        if self.job_manager.has_unfinished_job():
            pending = self.job_manager.get_pending_queries()
            count = len(pending)
            self.log_to_console(f"Found unfinished job with {count} pending queries.")
            self.btn_resume_ui.configure(state="normal", text=f"RESUME JOB ({count} pending)")
            msg = (
                f"An interrupted job was found with {count} pending queries.\n"
                "Go to 'New Scrape' -> 'RESUME' to continue."
            )
            messagebox.showinfo("Resume Available", msg)

    def start_scraping(self) -> None:
        self.save_settings(silent=True)

        raw_text = self.txt_input.get("1.0", "end")
        queries = [line.strip() for line in raw_text.splitlines() if line.strip()]

        if not queries:
            messagebox.showerror("Error", "Please enter at least one keyword (one per line).")
            return

        invalid_queries = [q for q in queries if not validate_input("search_query", q)]
        if invalid_queries:
            preview = "\n".join(invalid_queries[:5])
            suffix = "\n..." if len(invalid_queries) > 5 else ""
            messagebox.showerror(
                "Invalid Input",
                f"The following queries contain invalid characters:\n\n{preview}{suffix}",
            )
            return

        try:
            max_results = int(self.max_results_var.get())
            if max_results < 0 or max_results > 100000:
                messagebox.showerror("Invalid Input", "Max Results must be between 0 and 100,000")
                return
        except ValueError:
            messagebox.showerror("Invalid Input", "Max Results must be a valid number")
            return

        self.run_job(queries=queries, resume=False)

    def resume_scraping(self) -> None:
        self.run_job(resume=True)

    def run_job(self, queries: List[str] | None = None, resume: bool = False) -> None:
        self.btn_start.configure(state="disabled")
        self.btn_resume_ui.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="RUNNING", text_color="#FFA500")

        self.config_manager.save_config({
            "creds_file": self.creds_file_path.get(),
            "max_results": self.max_results_var.get(),
            "headless": self.headless_var.get(),
            "export_csv": self.csv_export_var.get(),
        })

        args: Dict[str, Any] = {
            "input_queries": queries,
            "creds_file": self.creds_file_path.get(),
            "total": int(self.max_results_var.get()) if self.max_results_var.get().isdigit() else 0,
            "headless": self.headless_var.get(),
            "export_csv": self.csv_export_var.get(),
            "sheet_behavior": self.sheet_behavior_var.get(),
            "max_scroll_time": int(self.max_scroll_time_var.get()) if self.max_scroll_time_var.get().isdigit() else 300,
            "scroll_wait": int(self.scroll_wait_var.get()) if self.scroll_wait_var.get().isdigit() else 3000,
            "max_scroll_retries": int(self.max_retries_var.get()) if self.max_retries_var.get().isdigit() else 5,
            "resume": resume,
            "stats_queue": self.stats_queue,
            "scroll_amount_per_step": (
                int(self.scroll_amount_var.get()) if self.scroll_amount_var.get().isdigit() else 10000
            ),
            "auto_skip_timeout": int(self.auto_skip_var.get()) if self.auto_skip_var.get().isdigit() else 0,
            "smart_wait_enabled": self.smart_wait_var.get(),
            "use_feed_scroll": self.feed_scroll_var.get(),
            "export_sheets": self.sheets_export_var.get(),
            "export_db": self.db_export_var.get(),
            "auto_upload": self.auto_upload_var.get(),
            "auto_accept": self.auto_accept_var.get(),
            "manual_verification": self.manual_verify_var.get(),
            "interactive_controls": self.interactive_var.get(),
            "show_progress": self.show_progress_var.get(),
            "pre_filter_names": self.pre_filter_var.get(),
            "batch_db_ops": self.batch_db_var.get(),
            "cache_sheet_data": self.cache_sheet_var.get(),
        }

        self.select_frame("Dashboard")

        # Start Thread
        self.controller = ScraperController()
        self.scraper_thread = threading.Thread(target=self.run_scraper_logic, args=(args,), daemon=True)
        self.scraper_thread.start()

    def run_scraper_logic(self, args: Dict[str, Any]) -> None:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = TextRedirector(self.log_queue)
        sys.stderr = TextRedirector(self.log_queue)

        try:
            print("--- STARTING JOB ---")
            main_gui_wrapper.run_gui_mode(
                input_queries=args.get("input_queries"),
                creds_file=args["creds_file"],
                total=args["total"],
                headless=args["headless"],
                export_csv=args["export_csv"],
                controller=self.controller,
                sheet_behavior=args["sheet_behavior"],
                max_scroll_time=args["max_scroll_time"],
                scroll_wait=args["scroll_wait"],
                resume=args["resume"],
                stats_queue=args["stats_queue"],
                scroll_amount_per_step=args["scroll_amount_per_step"],
                auto_skip_timeout=args["auto_skip_timeout"],
                smart_wait_enabled=args["smart_wait_enabled"],
                use_feed_scroll=args["use_feed_scroll"],
                export_sheets=args["export_sheets"],
                export_db=args["export_db"],
                auto_upload=args["auto_upload"],
                auto_accept=args["auto_accept"],
                manual_verification=args["manual_verification"],
                interactive_controls=args["interactive_controls"],
                show_progress=args["show_progress"],
                pre_filter_names=args["pre_filter_names"],
                batch_db_ops=args["batch_db_ops"],
                cache_sheet_data=args["cache_sheet_data"],
            )
            print("--- JOB FINISHED ---")
            self.stats_queue.put({"type": "job_status", "status": "COMPLETED", "color": "#00FF00"})
        except Exception as e:
            self.logger.exception("Scraper job encountered an error: %s", e)
            print(f"CRITICAL ERROR: {e}")
            self.stats_queue.put({"type": "job_status", "status": "ERROR", "color": "#FF4444"})
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            self.stats_queue.put({"type": "job_finished"})

    def reset_ui_state(self) -> None:
        self.btn_start.configure(state="normal")
        self.btn_resume_ui.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        if self.job_manager.has_unfinished_job():
            self.btn_resume_ui.configure(state="normal")

    def stop_scraping(self) -> None:
        if self.controller:
            self.controller.stop()
            self.log_to_console(">>> STOP SIGNAL SENT...")

    def log_to_console(self, msg: object) -> None:
        self.log_queue.put(str(msg) + "\n")

    def update_console(self) -> None:
        # 1. Process Logs
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.console_box.configure(state="normal")

            if "\r" in msg:
                continue

            tag = "normal"
            lower = msg.lower()
            if any(term in lower for term in ("0 error", "no error", "passed", "success")) or "✅" in msg:
                tag = "success"
            elif any(term in lower for term in ("warning", "warn")) or "⚠️" in msg:
                tag = "warning"
            elif any(term in lower for term in ("error", "fail", "fatal", "exception")) or "❌" in msg:
                tag = "error"

            tk_textbox = getattr(self.console_box, "_textbox", None)
            if tk_textbox:
                tk_textbox.insert("end", msg, (tag,))
            else:
                self.console_box.insert("end", msg)

            self.console_box.see("end")
            self.console_box.configure(state="disabled")

        # 2. Process Stats and Thread Messages
        while not self.stats_queue.empty():
            stat = self.stats_queue.get()
            st_type = stat.get("type")
            if st_type == "stats_update":
                leads = stat.get("total_leads", 0)
                done = stat.get("completed", 0)
                total = stat.get("total_queries", 0)
                self.lbl_leads.configure(text=f"Leads: {leads}")
                self.lbl_status.configure(text=f"RUNNING ({done}/{total})")
            elif st_type == "job_status":
                self.lbl_status.configure(
                    text=stat.get("status", "IDLE"),
                    text_color=stat.get("color", "#2CC985"),
                )
            elif st_type == "job_finished":
                self.reset_ui_state()

        self.after(50, self.update_console)

    def browse_creds(self) -> None:
        filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if filename:
            self.creds_file_path.set(filename)

    def open_data_folder(self) -> None:
        folder = "GMaps Data"
        try:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
            os.startfile(os.path.abspath(folder))
        except OSError as e:
            messagebox.showerror("Error", f"Could not open folder '{folder}': {e}")

    def run_diagnostics_gui(self) -> None:
        """Run diagnostics check with test selection popup."""
        test_window = ctk.CTkToplevel(self)
        test_window.title("Select Tests")
        test_window.geometry("400x500")
        test_window.attributes("-topmost", True)

        ctk.CTkLabel(test_window, text="Select Tests to Run", font=("Arial", 16, "bold")).pack(pady=20)

        test_vars: Dict[str, ctk.BooleanVar] = {}
        tests = [
            ("Config File Validation", "test_config.py"),
            ("Environment Verification", "test_env.py"),
            ("Data Extraction Test", "test_data_extraction.py"),
            ("Google Sheets Connection", "test_sheets.py"),
            ("Headless Scraping Test", "test_headless_scrape.py"),
            ("Headed Scraping Test", "test_headed_scrape.py"),
        ]

        scrollable_frame = ctk.CTkScrollableFrame(test_window, width=350, height=300)
        scrollable_frame.pack(pady=10)

        for test_name, test_file in tests:
            var = ctk.BooleanVar(master=test_window, value=True)
            test_vars[test_file] = var
            ctk.CTkCheckBox(scrollable_frame, text=test_name, variable=var).pack(pady=5, anchor="w")

        button_frame = ctk.CTkFrame(test_window, fg_color="transparent")
        button_frame.pack(pady=10)

        def run_tests() -> None:
            selected_tests = [f for f, var in test_vars.items() if var.get()]
            test_window.destroy()
            self.select_frame("Logs")
            self.log_to_console("\n--- RUNNING DIAGNOSTICS ---")

            def run_test_thread() -> None:
                for test_file in selected_tests:
                    test_path = os.path.join("test", test_file)
                    if os.path.exists(test_path):
                        try:
                            self.log_to_console(f"\n🔍 Running: {test_file}")
                            result = subprocess.run(
                                [sys.executable, test_path],
                                capture_output=True,
                                text=True,
                                timeout=180,
                                check=False,
                            )
                            if result.returncode == 0:
                                self.log_to_console(f"✅ {test_file} PASSED")
                                self.log_to_console(result.stdout)
                            else:
                                self.log_to_console(f"❌ {test_file} FAILED")
                                self.log_to_console(result.stderr)
                        except subprocess.SubprocessError as e:
                            self.log_to_console(f"❌ {test_file} ERROR: {e}")
                    else:
                        self.log_to_console(f"⚠️  {test_file} not found")

                self.log_to_console("\n--- DIAGNOSTICS COMPLETE ---")

            threading.Thread(target=run_test_thread, daemon=True).start()

        ctk.CTkButton(
            button_frame, text="Run Selected Tests", command=run_tests, fg_color="#2CC985", width=150
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame, text="Cancel", command=test_window.destroy, fg_color="#555555", width=100
        ).pack(side="left", padx=5)

    def install_browsers_gui(self) -> None:
        """Launches a separate process to install browsers with Visual Feedback."""
        msg = (
            "This will download Playwright browsers (~150MB) to a shared folder.\n"
            "It may take a minute. Continue?"
        )
        if not messagebox.askyesno("Install Browsers", msg):
            return

        top = ctk.CTkToplevel(self)
        top.title("Installing Browsers...")
        top.geometry("400x200")
        top.attributes("-topmost", True)

        lbl = ctk.CTkLabel(top, text="Downloading & Installing Browsers...\nPlease Wait.", font=("Arial", 14))
        lbl.pack(pady=20)

        progress = ctk.CTkProgressBar(top, width=300)
        progress.pack(pady=10)
        progress.start()

        status_lbl = ctk.CTkLabel(top, text="Starting...", text_color="#AAAAAA")
        status_lbl.pack(pady=5)

        def run_install() -> None:
            self.log_to_console(">>> INSTALLATION STARTED...")
            try:
                env = os.environ.copy()
                env["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_BROWSERS_PATH

                if getattr(sys, "frozen", False):
                    cmd = [sys.executable, "--install-browsers"]
                else:
                    cmd = [sys.executable, "-m", "playwright", "install", "chromium"]

                process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )

                while True:
                    line = process.stdout.readline() if process.stdout else ""
                    if not line and process.poll() is not None:
                        break
                    if line:
                        txt = line.strip()
                        if txt:
                            self.log_to_console(f"[INSTALL] {txt}")
                            try:
                                top.after(0, lambda t=txt: status_lbl.configure(text=t[:50]))
                            except (tk.TclError, RuntimeError):
                                pass

                rc = process.poll()
                if rc == 0:
                    try:
                        top.after(0, lambda: messagebox.showinfo("Success", "Browsers Installed Successfully!"))
                    except (tk.TclError, RuntimeError):
                        pass
                    self.log_to_console("✅ Browsers Installed Successfully.")
                else:
                    try:
                        top.after(0, lambda: messagebox.showerror("Error", "Installation failed. Check logs."))
                    except (tk.TclError, RuntimeError):
                        pass
                    self.log_to_console("❌ Browser Installation Failed. Check output above.")
            except (subprocess.SubprocessError, OSError) as e:
                err_msg = str(e)
                try:
                    top.after(0, lambda msg=err_msg: messagebox.showerror("Error", f"Failed: {msg}"))
                except (tk.TclError, RuntimeError):
                    pass
                self.log_to_console(f"❌ Install Exception: {err_msg}")
            finally:
                try:
                    top.after(0, top.destroy)
                except (tk.TclError, RuntimeError):
                    pass

        threading.Thread(target=run_install, daemon=True).start()

    def save_settings(self, silent: bool = False) -> bool:
        """Saves current settings to config file."""
        try:
            mr = int(self.max_results_var.get())
            if mr < 0 or mr > 100000:
                if not silent:
                    messagebox.showerror("Invalid Setting", "Max Results must be between 0 and 100,000")
                return False
        except ValueError:
            if not silent:
                messagebox.showerror("Invalid Setting", "Max Results must be a valid number")
            return False

        data = {
            "input_file": self.input_file_path.get(),
            "creds_file": self.creds_file_path.get(),
            "max_results": self.max_results_var.get(),
            "headless": self.headless_var.get(),
            "export_csv": self.csv_export_var.get(),
            "sheet_behavior": self.sheet_behavior_var.get(),
            "max_scroll_time": self.max_scroll_time_var.get(),
            "scroll_wait": self.scroll_wait_var.get(),
            "max_scroll_retries": self.max_retries_var.get(),
            "scroll_amount_per_step": self.scroll_amount_var.get(),
            "auto_skip_timeout": self.auto_skip_var.get(),
            "smart_wait_enabled": self.smart_wait_var.get(),
            "use_feed_scroll": self.feed_scroll_var.get(),
            "export_sheets": self.sheets_export_var.get(),
            "export_db": self.db_export_var.get(),
            "auto_upload": self.auto_upload_var.get(),
            "auto_accept": self.auto_accept_var.get(),
            "manual_verification": self.manual_verify_var.get(),
            "interactive_controls": self.interactive_var.get(),
            "show_progress": self.show_progress_var.get(),
            "pre_filter_names": self.pre_filter_var.get(),
            "batch_db_ops": self.batch_db_var.get(),
            "cache_sheet_data": self.cache_sheet_var.get(),
        }
        self.config_manager.save_config(data)
        if not silent:
            messagebox.showinfo("Settings Saved", "Your configuration has been saved successfully.")
        return True


if __name__ == "__main__":
    if "--install-browsers" in sys.argv:
        print(">>> STARTING INTERNAL BROWSER INSTALLER...")
        try:
            if getattr(sys, "frozen", False):
                from playwright.__main__ import main as pw_main

                sys.argv = ["playwright", "install", "chromium"]
                pw_main()
            else:
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print(">>> INSTALLATION SUCCESSFUL")
            sys.exit(0)
        except Exception as err:
            print(f">>> INSTALLATION FAILED: {err}")
            sys.exit(1)
    app = ScraperGUI()
    app.mainloop()
