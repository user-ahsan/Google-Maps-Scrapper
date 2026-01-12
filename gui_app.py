import customtkinter as ctk
import sys
import threading
import queue
import os
import re
import subprocess
from tkinter import filedialog, messagebox
import tkinter as tk

# Core Modules
from src.controller import ScraperController
from src.config_manager import ConfigManager
from src import resource_utils
from src.logger import setup_logger
from src.job_manager import JobManager

# --- THEME SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- CONSTANTS ---
PLAYWRIGHT_BROWSERS_PATH = resource_utils.get_browsers_path()
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_BROWSERS_PATH

class TextRedirector(object):
    """Redirects stdout/stderr to a queue for the GUI to consume."""
    def __init__(self, widget_queue, tag="stdout"):
        self.widget_queue = widget_queue
        self.tag = tag
 
    def write(self, str_val):
        # Strip ANSI codes for clean logs
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', str_val)
        self.widget_queue.put(clean_text)
        
    def flush(self):
        pass

class ScraperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
 
        # --- CONFIGURATION ---
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.logger = setup_logger("GUILogger")
        self.job_manager = JobManager()
        
        # Window Config
        self.title("Google Maps Scraper Pro")
        self.geometry("1100x800")
        
        # State
        self.controller = ScraperController()
        self.log_queue = queue.Queue()
        self.stats_queue = queue.Queue() # New Queue
        self.scraper_thread = None
        self.active_frame = None
        
        # Variables
        self.input_file_path = ctk.StringVar(value=self.config.get("input_file", ""))
        self.creds_file_path = ctk.StringVar(value=self.config.get("creds_file", "credentials.json"))
        self.max_results_var = ctk.StringVar(value=self.config.get("max_results", "100"))
        self.headless_var = ctk.BooleanVar(value=self.config.get("headless", True))
        self.csv_export_var = ctk.BooleanVar(value=self.config.get("export_csv", True))
        
        self.sheet_behavior_var = ctk.StringVar(value=self.config.get("sheet_behavior", "Append"))
        self.max_scroll_time_var = ctk.StringVar(value=self.config.get("max_scroll_time", "300"))
        self.scroll_wait_var = ctk.StringVar(value=self.config.get("scroll_wait", "3000")) # Default 3000ms
        self.max_retries_var = ctk.StringVar(value=self.config.get("max_scroll_retries", "5"))

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

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="GMap Scraper", 
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Nav Buttons
        self.btn_dashboard = self.create_nav_button("📊 Dashboard", "Dashboard", 1)
        self.btn_scrape = self.create_nav_button("🕸️ New Scrape", "Scrape", 2)
        self.btn_settings = self.create_nav_button("⚙️ Settings", "Settings", 3)
        self.btn_logs = self.create_nav_button("📝 Logs", "Logs", 4)
        
        # Status / Controls (Bottom)
        self.controls_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.controls_frame.grid(row=6, column=0, padx=10, pady=20, sticky="ew")
        
        self.btn_stop = ctk.CTkButton(
            self.controls_frame, 
            text="STOP JOB",
            fg_color="#FF4444", 
            hover_color="#CC0000",
            state="disabled",
            command=self.stop_scraping
        )
        self.btn_stop.pack(fill="x")

    def create_nav_button(self, text, value, row):
        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            fg_color="transparent",
            text_color=("gray90", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=lambda v=value: self.select_frame(v)
        )
        btn.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        return btn

    def create_pages(self):
        # We create all frames and stack them, showing one at a time.
        self.frames = {}
        
        # 1. Dashboard Frame
        self.frames["Dashboard"] = self.create_dashboard_frame()
        self.frames["Scrape"] = self.create_scrape_frame()
        self.frames["Settings"] = self.create_settings_frame()
        self.frames["Logs"] = self.create_logs_frame()
        
        for f in self.frames.values():
            f.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

    # --- PAGES ---
    
    def create_dashboard_frame(self):
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

    def create_scrape_frame(self):
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
            command=self.start_scraping
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_resume_ui = ctk.CTkButton(
            btn_box,
            text="RESUME PREVIOUS",
            font=("Arial", 16, "bold"),
            height=50,
            fg_color="#FFA500",
            hover_color="#CC8400",
            state="disabled", # Enabled if resume available
            command=self.resume_scraping
        )
        self.btn_resume_ui.pack(side="left", fill="x", expand=True, padx=(10, 0))

        return f

    def create_settings_frame(self):
        f = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        ctk.CTkLabel(f, text="Settings", font=("Arial", 28, "bold")).pack(pady=30, padx=40, anchor="w")
        
        # --- Form Helper ---
        def add_section(title):
            ctk.CTkLabel(f, text=title, font=("Arial", 16, "bold"), text_color="#2CC985").pack(pady=(20, 10), padx=40, anchor="w")

        def add_field(label, var):
            row = ctk.CTkFrame(f, fg_color="transparent")
            row.pack(fill="x", padx=40, pady=5)
            ctk.CTkLabel(row, text=label, width=150, anchor="w").pack(side="left")
            ctk.CTkEntry(row, textvariable=var, width=300).pack(side="left")
            
        def add_switch(label, var):
            ctk.CTkSwitch(f, text=label, variable=var).pack(padx=40, pady=10, anchor="w")

        # General
        add_section("General Config")
        add_field("Max Results / Query:", self.max_results_var)
        add_switch("Headless Mode (Background)", self.headless_var)
        add_switch("Export to CSV Files", self.csv_export_var)
        
        # Files
        add_section("File Paths")
        
        # Creds (Manual Browse)
        r_creds = ctk.CTkFrame(f, fg_color="transparent")
        r_creds.pack(fill="x", padx=40, pady=5)
        ctk.CTkLabel(r_creds, text="Credentials JSON:", width=150, anchor="w").pack(side="left")
        ctk.CTkEntry(r_creds, textvariable=self.creds_file_path, width=220).pack(side="left")
        ctk.CTkButton(r_creds, text="Browse", width=70, command=self.browse_creds).pack(side="left", padx=10)

        # Advanced
        add_section("Advanced")
        add_field("Max Scroll Time (s):", self.max_scroll_time_var)
        add_field("Scroll Wait/Interval (ms):", self.scroll_wait_var)
        add_field("Max Retries:", self.max_retries_var)
        
        ctk.CTkLabel(f, text="Sheet Behavior:", width=150, anchor="w").pack(padx=40, pady=(10,0), anchor="w")
        ctk.CTkOptionMenu(f, values=["Append", "Overwrite", "New Sheet"], variable=self.sheet_behavior_var).pack(padx=40, pady=5, anchor="w")

        # System Tools
        add_section("System Tools")
        ctk.CTkButton(f, text="Re-Install Browsers", command=self.install_browsers_gui, fg_color="#555555").pack(padx=40, pady=5, anchor="w")
        ctk.CTkButton(f, text="Run Diagnostics", command=self.run_diagnostics_gui, fg_color="#4444aa").pack(padx=40, pady=5, anchor="w")
        ctk.CTkButton(f, text="Open Data Folder", command=self.open_data_folder, fg_color="#333333").pack(padx=40, pady=5, anchor="w")

        # Save Button
        ctk.CTkButton(f, text="SAVE SETTINGS", command=self.save_settings, fg_color="#2CC985", height=40, font=("Arial", 14, "bold")).pack(padx=40, pady=30, anchor="w", fill="x")

        return f

    def create_logs_frame(self):
        f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        ctk.CTkLabel(f, text="System Logs", font=("Arial", 28, "bold")).pack(pady=30, padx=40, anchor="w")
        
        self.console_box = ctk.CTkTextbox(f, font=("Consolas", 12), text_color="#DDDDDD", fg_color="#111111", wrap="none")
        self.console_box.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        self.console_box.configure(state="disabled")
        
        # Tags - reused logic
        self.console_box._textbox.tag_config("error", foreground="#FF4444")
        self.console_box._textbox.tag_config("success", foreground="#00FF00")
        self.console_box._textbox.tag_config("warning", foreground="#FFA500")
        
        return f

    # --- LOGIC ---
    
    def select_frame(self, name):
        self.active_frame = name
        # Hide all
        for f in self.frames.values():
            f.grid_forget()
        # Show selected
        self.frames[name].grid(row=0, column=1, sticky="nsew")
        
        # Color Active Button
        # (Simplified: Just resetting all colors would be better but keeping simple)
        
    def check_resume_state(self):
        if self.job_manager.has_unfinished_job():
            pending = self.job_manager.get_pending_queries()
            count = len(pending)
            self.log_to_console(f"Found unfinished job with {count} pending queries.")
            self.btn_resume_ui.configure(state="normal", text=f"RESUME JOB ({count} pending)")
            messagebox.showinfo("Resume Available", f"An interrupted job was found with {count} pending queries.\nGo to 'New Scrape' -> 'RESUME' to continue.")
            
    def start_scraping(self):
        self.save_settings(silent=True) # Auto-save on start
        
        raw_text = self.txt_input.get("1.0", "end")
        queries = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        if not queries:
            messagebox.showerror("Error", "Please enter at least one keyword (one per line).")
            return
            
        self.run_job(queries=queries, resume=False)

    def resume_scraping(self):
        self.run_job(resume=True)

    def run_job(self, queries=None, resume=False):
        # UI Lock
        self.btn_start.configure(state="disabled")
        self.btn_resume_ui.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        
        self.lbl_status.configure(text="RUNNING", text_color="#FFA500")
        
        # Config
        self.config_manager.save_config({
            "creds_file": self.creds_file_path.get(),
            "max_results": self.max_results_var.get(),
            "headless": self.headless_var.get(),
            "export_csv": self.csv_export_var.get(),
        })

        args = {
            "input_queries": queries,
            "creds_file": self.creds_file_path.get(),
            "total": int(self.max_results_var.get()) if self.max_results_var.get().isdigit() else 0,
            "headless": self.headless_var.get(),
            "export_csv": self.csv_export_var.get(),
            "sheet_behavior": self.sheet_behavior_var.get(),
            "max_scroll_time": int(self.max_scroll_time_var.get()),
            "scroll_wait": int(self.scroll_wait_var.get()),
            "max_scroll_retries": int(self.max_retries_var.get()),
            "resume": resume,
            "stats_queue": self.stats_queue
        }
        
        self.select_frame("Dashboard") # Auto-switch to logs or Dashboard? User said hide logs.
        # Let's switch to Dashboard but logs are background. 
        # Actually user said "Hide by Default". So maybe stay on Dashboard.
        # But we need feedback. I'll switch to Dashboard and rely on status label.
        self.select_frame("Dashboard")
        
        # Start Thread
        self.controller = ScraperController() 
        self.scraper_thread = threading.Thread(target=self.run_scraper_logic, args=(args,))
        self.scraper_thread.daemon = True 
        self.scraper_thread.start()

    def run_scraper_logic(self, args):
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = TextRedirector(self.log_queue)
        sys.stderr = TextRedirector(self.log_queue)
        
        try:
            print("--- STARTING JOB ---")
            import main_gui_wrapper 
            
            main_gui_wrapper.run_gui_mode(
                input_queries=args.get("input_queries"),
                # We can skip input_file if queries present
                creds_file=args["creds_file"],
                total=args["total"],
                headless=args["headless"],
                export_csv=args["export_csv"],
                controller=self.controller,
                sheet_behavior=args["sheet_behavior"],
                max_scroll_time=args["max_scroll_time"],
                scroll_wait=args["scroll_wait"],
                resume=args["resume"],
                stats_queue=args["stats_queue"]
            )
            print("--- JOB FINISHED ---")
            self.after(0, lambda: self.lbl_status.configure(text="COMPLETED", text_color="#00FF00"))
            
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            self.after(0, lambda: self.lbl_status.configure(text="ERROR", text_color="#FF4444"))
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            self.after(0, self.reset_ui_state)

    def reset_ui_state(self):
        self.btn_start.configure(state="normal")
        self.btn_resume_ui.configure(state="disabled") # Check again?
        self.btn_stop.configure(state="disabled")
        # Check resume availability again
        if self.job_manager.has_unfinished_job():
             self.btn_resume_ui.configure(state="normal")

    def stop_scraping(self):
        if self.controller:
            self.controller.stop()
            self.log_to_console(">>> STOP SIGNAL SENT...")

    # --- UTILS ---
    def log_to_console(self, msg):
        self.log_queue.put(str(msg) + "\n")

    def update_console(self):
        # 1. Process Logs
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.console_box.configure(state="normal")
            
            # Filter out \r messages to prevent spam, or handle them
            if '\r' in msg:
                continue # Skip progress bar logs in GUI console to keep it clean

            tag = "normal"
            lower = msg.lower()
            if "error" in lower or "fail" in lower: tag = "error"
            elif "success" in lower: tag = "success"
            
            self.console_box._textbox.insert("end", msg, (tag,))
            self.console_box.see("end")
            self.console_box.configure(state="disabled")
            
        # 2. Process Stats
        while not self.stats_queue.empty():
            stat = self.stats_queue.get()
            if stat.get("type") == "stats_update":
                leads = stat.get("total_leads", 0)
                done = stat.get("completed", 0)
                total = stat.get("total_queries", 0)
                self.lbl_leads.configure(text=f"Leads: {leads}")
                self.lbl_status.configure(text=f"RUNNING ({done}/{total})")

        self.after(50, self.update_console)

    def browse_creds(self):
         filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
         if filename: self.creds_file_path.set(filename)

    def open_data_folder(self):
        folder = "GMaps Data"
        if not os.path.exists(folder): os.makedirs(folder)
        os.startfile(os.path.abspath(folder))

    def run_diagnostics_gui(self):
        """Run the diagnostics check in the main console."""
        self.select_frame("Logs")
        self.log_to_console("\n--- RUNNING DIAGNOSTICS ---")
        
        def diag_thread():
            try:
                # Redirect Stdout
                original_stdout = sys.stdout
                sys.stdout = TextRedirector(self.log_queue)
                
                # Use main from root
                import main
                main.run_diagnostics(force_offline=True) 
                
                print("--- DIAGNOSTICS COMPLETE ---")
            except Exception as e:
                print(f"Diagnostics Error: {e}")
            finally:
                sys.stdout = original_stdout

        threading.Thread(target=diag_thread, daemon=True).start()

    def install_browsers_gui(self):
        """Launches a separate process to install browsers with Visual Feedback."""
        if not messagebox.askyesno("Install Browsers", "This will download Playwright browsers (~150MB) to a shared folder. It may take a minute. Continue?"):
            return

        # Create Popup Window
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
        
        def run_install():
            self.log_to_console(">>> INSTALLATION STARTED...")
            try:
                # Prepare env
                env = os.environ.copy()
                env["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_BROWSERS_PATH
                
                # Determine command
                if getattr(sys, 'frozen', False):
                    # FROZEN: Calls itself with special flag
                    cmd = [sys.executable, "--install-browsers"]
                else:
                    # DEV: Calls module
                    cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
                
                process = subprocess.Popen(
                    cmd, 
                    env=env, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        txt = line.strip()
                        if txt:
                            # Log to MAIN console as well
                            self.log_to_console(f"[INSTALL] {txt}")
                            # Update label in thread-safe way
                            top.after(0, lambda t=txt: status_lbl.configure(text=t[:50]))
                
                rc = process.poll()
                
                if rc == 0:
                    top.after(0, lambda: messagebox.showinfo("Success", "Browsers Installed Successfully!"))
                    self.log_to_console("✅ Browsers Installed Successfully.")
                else:
                    top.after(0, lambda: messagebox.showerror("Error", "Installation failed. Check logs."))
                    self.log_to_console("❌ Browser Installation Failed. Check output above.")

            except Exception as e:
                top.after(0, lambda: messagebox.showerror("Error", f"Failed: {e}"))
                self.log_to_console(f"❌ Install Exception: {e}")
            finally:
                top.after(0, top.destroy)

        threading.Thread(target=run_install, daemon=True).start()

    def save_settings(self, silent=False):
        """Saves current settings to config file."""
        data = {
            "input_file": self.input_file_path.get(),
            "creds_file": self.creds_file_path.get(),
            "max_results": self.max_results_var.get(),
            "headless": self.headless_var.get(),
            "export_csv": self.csv_export_var.get(),
            "sheet_behavior": self.sheet_behavior_var.get(),
            "max_scroll_time": self.max_scroll_time_var.get(),
            "scroll_wait": self.scroll_wait_var.get(),
            "max_scroll_retries": self.max_retries_var.get()
        }
        self.config_manager.save_config(data)
        if not silent:
            messagebox.showinfo("Settings Saved", "Your configuration has been saved successfully.")

if __name__ == "__main__":
    if "--install-browsers" in sys.argv:
        # Install logic
        sys.exit(0)
    app = ScraperGUI()
    app.mainloop()
