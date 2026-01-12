import customtkinter as ctk
import sys
import threading
import queue
import os
import io
import time
import subprocess
from tkinter import filedialog, messagebox
import tkinter as tk
from src.controller import ScraperController
from src.config_manager import ConfigManager
from src import resource_utils
from src.logger import setup_logger

# --- THEME SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- CONSTANTS ---
PLAYWRIGHT_BROWSERS_PATH = resource_utils.get_browsers_path()
# Ensure env var is set for the current process so playright sees it
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_BROWSERS_PATH

class TextRedirector(object):
    """Redirects stdout/stderr to a queue for the GUI to consume."""
    def __init__(self, widget_queue, tag="stdout"):
        self.widget_queue = widget_queue
        self.tag = tag
 
    def write(self, str_val):
        self.widget_queue.put(str_val)
        
    def flush(self):
        pass

class ScraperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
 
        # --- CONFIGURATION ---
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.logger = setup_logger("GUILogger")
        self.logger.info("GUI Started")
 
        # Window Config
        self.title("Google Maps Scraper Pro")
        self.geometry("1000x850") # Slightly taller for new buttons
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
 
        # State Variables
        self.controller = ScraperController()
        self.log_queue = queue.Queue()
        self.scraper_thread = None
        
        # Variables bound to Config
        self.input_file_path = ctk.StringVar(value=self.config.get("input_file", ""))
        self.creds_file_path = ctk.StringVar(value=self.config.get("creds_file", "credentials.json"))
        self.max_results_var = ctk.StringVar(value=self.config.get("max_results", "100"))
        self.headless_var = ctk.BooleanVar(value=self.config.get("headless", True))
        
        self.sheet_behavior_var = ctk.StringVar(value=self.config.get("sheet_behavior", "Append"))
        self.max_scroll_time_var = ctk.StringVar(value=self.config.get("max_scroll_time", "300"))
        self.max_retries_var = ctk.StringVar(value=self.config.get("max_scroll_retries", "5"))
 
        # --- UI CONSTRUCTION ---
        self.create_sidebar()
        self.create_main_area()
        
        # --- INITIALIZATION CHECKS ---
        self.after(500, self.check_browsers_silent)
 
    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)
 
        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="GMap Scraper", 
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#FFFFFF" 
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
 
        # --- TABVIEW for Settings ---
        self.settings_tabs = ctk.CTkTabview(self.sidebar_frame, width=250, height=500) # Taller
        self.settings_tabs.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.tab_general = self.settings_tabs.add("General")
        self.tab_advanced = self.settings_tabs.add("Advanced")
        
        # --- GENERAL TAB ---
        self.create_general_tab()
        
        # --- ADVANCED TAB ---
        self.create_advanced_tab()
 
        # --- CONTROLS ---
        self.create_control_section()
 
    def create_general_tab(self):
        # Helper for consistency
        def label(text, row):
            l = ctk.CTkLabel(self.tab_general, text=text, anchor="w", text_color="#DDDDDD", font=("Arial", 12, "bold"))
            l.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
            return l
 
        # Input File
        label("Input Queries File:", 0)
        self.input_entry = ctk.CTkEntry(self.tab_general, textvariable=self.input_file_path, placeholder_text="Select input.txt...")
        self.input_entry.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        ctk.CTkButton(self.tab_general, text="Browse", width=80, command=self.browse_input).grid(row=2, column=0, padx=10, sticky="e")
 
        # Credentials
        label("Credentials JSON:", 3)
        self.creds_entry = ctk.CTkEntry(self.tab_general, textvariable=self.creds_file_path, placeholder_text="credentials.json")
        self.creds_entry.grid(row=4, column=0, padx=10, pady=(0, 5), sticky="ew")
        ctk.CTkButton(self.tab_general, text="Browse", width=80, command=self.browse_creds).grid(row=5, column=0, padx=10, sticky="e")
 
        # Max Results
        label("Max Results (per query):", 6)
        self.max_results_entry = ctk.CTkEntry(self.tab_general, textvariable=self.max_results_var, placeholder_text="e.g. 100")
        self.max_results_entry.grid(row=7, column=0, padx=10, pady=(0, 5), sticky="ew")
 
        # Headless Toggle
        self.headless_switch = ctk.CTkSwitch(
            self.tab_general, 
            text="Headless Mode (Background)", 
            variable=self.headless_var, 
            onvalue=True, 
            offvalue=False,
            text_color="#EEEEEE"
        )
        self.headless_switch.grid(row=8, column=0, padx=10, pady=20, sticky="w")
 
    def create_advanced_tab(self):
        def label(text, row):
            l = ctk.CTkLabel(self.tab_advanced, text=text, anchor="w", text_color="#DDDDDD", font=("Arial", 12, "bold"))
            l.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
 
        # Sheet Behavior
        label("Sheet Saving Behavior:", 0)
        self.sheet_behavior_menu = ctk.CTkOptionMenu(
            self.tab_advanced,
            values=["Append", "Overwrite", "New Sheet"],
            variable=self.sheet_behavior_var
        )
        self.sheet_behavior_menu.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        # Max Scroll Time
        label("Max Scroll Time (seconds):", 2)
        self.scroll_time_entry = ctk.CTkEntry(self.tab_advanced, textvariable=self.max_scroll_time_var)
        self.scroll_time_entry.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        # Max Retries
        label("Max Scroll Retries:", 4)
        self.max_retries_entry = ctk.CTkEntry(self.tab_advanced, textvariable=self.max_retries_var)
        self.max_retries_entry.grid(row=5, column=0, padx=10, pady=(0, 5), sticky="ew")
 
        # Browser Tools
        label("System Tools:", 7)
        
        # 1. Install Browsers
        self.btn_install = ctk.CTkButton(
            self.tab_advanced, 
            text="Re-Install Browsers & Fix", 
            command=self.install_browsers_gui,
            fg_color="#555555",
            hover_color="#333333"
        )
        self.btn_install.grid(row=8, column=0, padx=10, pady=(5, 5), sticky="ew")

        # 2. Run Diagnostics
        self.btn_diag = ctk.CTkButton(
            self.tab_advanced, 
            text="Run System Diagnostics", 
            command=self.run_diagnostics_gui,
            fg_color="#4444aa",
            hover_color="#333399"
        )
        self.btn_diag.grid(row=9, column=0, padx=10, pady=(5, 5), sticky="ew")

        # 3. Open Data Folder
        self.btn_open_data = ctk.CTkButton(
            self.tab_advanced, 
            text="Open Data Folder", 
            command=self.open_data_folder,
            fg_color="#333333",
            hover_color="#111111"
        )
        self.btn_open_data.grid(row=10, column=0, padx=10, pady=(5, 5), sticky="ew")

 
    def create_control_section(self):
        # Frame at bottom of sidebar
        self.control_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.control_frame.grid(row=10, column=0, padx=20, pady=20, sticky="ew")
        
        self.btn_start = ctk.CTkButton(
            self.control_frame, 
            text="START SCRAPING", 
            command=self.start_scraping, 
            fg_color="#2CC985", 
            text_color="white",
            hover_color="#229966",
            height=40,
            font=("Arial", 14, "bold")
        )
        self.btn_start.pack(fill="x", pady=(0, 10))
 
        self.btn_pause = ctk.CTkButton(
            self.control_frame, 
            text="PAUSE", 
            command=self.toggle_pause, 
            state="disabled", 
            fg_color="#FFA500", 
            text_color="white",
            hover_color="#CC8400"
        )
        self.btn_pause.pack(fill="x", pady=(0, 10))

        self.btn_skip = ctk.CTkButton(
            self.control_frame, 
            text="SKIP ITEM", 
            command=self.skip_item, 
            state="disabled", 
            fg_color="#3388FF", 
            text_color="white",
            hover_color="#0066CC"
        )
        self.btn_skip.pack(fill="x", pady=(0, 10))
 
        self.btn_stop = ctk.CTkButton(
            self.control_frame, 
            text="STOP", 
            command=self.stop_scraping, 
            state="disabled", 
            fg_color="#FF4444", 
            text_color="white",
            hover_color="#CC0000"
        )
        self.btn_stop.pack(fill="x")
 
    def create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1E1E1E") # Darker BG
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
 
        # Header Frame
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 5))
        
        self.console_label = ctk.CTkLabel(
            self.header_frame, 
            text="Live Console Output", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        self.console_label.pack(side="left")
        
        self.btn_copy = ctk.CTkButton(
            self.header_frame,
            text="Copy Output",
            width=80,
            height=24,
            fg_color="#444444",
            command=self.copy_console_output
        )
        self.btn_copy.pack(side="right")
 
        # Console (Rich Text)
        self.console_box = ctk.CTkTextbox(
            self.main_frame, 
            width=600, 
            font=("Consolas", 12),
            text_color="#FFFFFF", # Default White
            fg_color="#000000",
            corner_radius=5
        )
        self.console_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.console_box.configure(state="disabled")
        
        # Tags
        self.console_box._textbox.tag_config("error", foreground="#FF4444")
        self.console_box._textbox.tag_config("success", foreground="#00FF00")
        self.console_box._textbox.tag_config("warning", foreground="#FFA500")
        self.console_box._textbox.tag_config("info", foreground="#00CCFF")
        self.console_box._textbox.tag_config("normal", foreground="#FFFFFF")
 
        # Start Log Polling
        self.after(100, self.update_console)
 
    # --- LOGIC & HANDLERS ---
    
    def save_current_settings(self):
        data = {
            "input_file": self.input_file_path.get(),
            "creds_file": self.creds_file_path.get(),
            "max_results": self.max_results_var.get(),
            "headless": self.headless_var.get(),
            "sheet_behavior": self.sheet_behavior_var.get(),
            "max_scroll_time": self.max_scroll_time_var.get(),
            "max_scroll_retries": self.max_retries_var.get()
        }
        self.config_manager.save_config(data)
 
    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filename: 
            self.input_file_path.set(filename)
            self.save_current_settings()
 
    def browse_creds(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if filename: 
            self.creds_file_path.set(filename)
            self.save_current_settings()
 
    def check_browsers_silent(self):
        """Check if browsers exist on startup. Use persistent path."""
        # Simple check: Does the folder exist and have content?
        if not os.path.exists(PLAYWRIGHT_BROWSERS_PATH) or not os.listdir(PLAYWRIGHT_BROWSERS_PATH):
            self.log_to_console("⚠️ Playwright browsers not found in persistent storage.")
            self.log_to_console(f"   Path: {PLAYWRIGHT_BROWSERS_PATH}")
            self.log_to_console("   Please go to Advanced > Re-Install Browsers.")
        else:
            self.log_to_console("✅ Playwright browsers found.")

    def open_data_folder(self):
        """Opens the data folder in File Explorer."""
        folder = "GMaps Data"
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(os.path.abspath(folder))
        self.log_to_console(f"ℹ️ Opened Data Folder: {os.path.abspath(folder)}")

    def run_diagnostics_gui(self):
        """Run the diagnostics check in the main console."""
        self.log_to_console("\n--- RUNNING DIAGNOSTICS ---")
        
        def diag_thread():
            try:
                # Redirect Stdout
                original_stdout = sys.stdout
                sys.stdout = TextRedirector(self.log_queue)
                
                # Import main and run diagnostics
                # Since we are in the same process, we can just call it
                # BUT we need to be careful about imports
                import main
                main.run_diagnostics(force_offline=True) # Force offline to skip sheet sync time if just testing
                
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
 
    def toggle_pause(self):
        if self.controller.is_paused():
            self.controller.resume()
            self.btn_pause.configure(text="PAUSE", fg_color="#FFA500")
            self.log_to_console(">>> RESUMING PROCESS...")
        else:
            self.controller.pause()
            self.btn_pause.configure(text="RESUME", fg_color="#228B22") # Greenish to signal 'Go'
            self.log_to_console(">>> PAUSE REQUESTED...")
 
    def stop_scraping(self):
        if self.controller:
            self.controller.stop()
            self.controller.resume() 
        self.log_to_console(">>> STOP REQUESTED. Finishing current item...")
        self.btn_stop.configure(state="disabled")
        self.btn_pause.configure(state="disabled")
 
    def skip_item(self):
        self.controller.skip()
        self.log_to_console(">>> SKIP REQUESTED. Moving to next...")
        
    def copy_console_output(self):
        try:
            txt = self.console_box.get("1.0", "end")
            self.clipboard_clear()
            self.clipboard_append(txt)
            self.log_to_console("ℹ️ Copied console output to clipboard.")
        except:
            self.log_to_console("⚠️ Failed to copy to clipboard.")

    def log_to_console(self, msg):
        self.log_queue.put(str(msg) + "\n")
 
    def update_console(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.console_box.configure(state="normal")
            
            # Simple keyword highlighting logic using Tkinter Tags
            tag = "normal"
            lower_msg = msg.lower()
            
            if "error" in lower_msg or "fail" in lower_msg or "critical" in lower_msg or "exception" in lower_msg or "❌" in msg:
                tag = "error"
            elif "success" in lower_msg or "pass" in lower_msg or "done" in lower_msg or "✅" in msg:
                tag = "success"
            elif "warning" in lower_msg or "warn" in lower_msg or "⚠️" in msg:
                tag = "warning"
            elif "info" in lower_msg or "stats" in lower_msg or "ℹ️" in msg:
                tag = "info"
            elif "[install]" in lower_msg:
                tag = "info"
            
            # Insert with tag
            self.console_box._textbox.insert("end", msg, (tag,))
            self.console_box.see("end")
            self.console_box.configure(state="disabled")
        self.after(50, self.update_console)
 
    def start_scraping(self):
        self.save_current_settings()
        
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_pause.configure(state="normal")
        self.btn_skip.configure(state="normal")
        self.console_box.configure(state="normal")
        self.console_box.delete("1.0", "end")
        self.console_box.configure(state="disabled")
 
        # Prepare Args
        args = {
            "input_file": self.input_file_path.get(),
            "creds_file": self.creds_file_path.get(),
            "total": int(self.max_results_var.get()) if self.max_results_var.get().isdigit() else 0,
            "headless": self.headless_var.get(),
            "sheet_behavior": self.sheet_behavior_var.get(),
            "max_scroll_time": int(self.max_scroll_time_var.get()) if self.max_scroll_time_var.get().isdigit() else 300,
            "max_retries": int(self.max_retries_var.get()) if self.max_retries_var.get().isdigit() else 5
        }
 
        if not args["input_file"] or not os.path.exists(args["input_file"]):
             self.log_to_console("ERROR: Invalid Input File Path")
             self.btn_start.configure(state="normal")
             return
             
        # Start Thread
        self.controller = ScraperController() 
        self.scraper_thread = threading.Thread(target=self.run_scraper_logic, args=(args,))
        self.scraper_thread.daemon = True 
        self.scraper_thread.start()
 
    def run_scraper_logic(self, args):
        # Redirect Stdout
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = TextRedirector(self.log_queue)
        sys.stderr = TextRedirector(self.log_queue)
 
        try:
            print("--- INITIALIZING SCRAPER ---")
            print("--------------------------------------------------")
            print(f"Stats: Max={args['total']} | Headless={args['headless']} | Sheet={args['sheet_behavior']}")
            
            # Import Wrapper
            import main_gui_wrapper 
            
            main_gui_wrapper.run_gui_mode(
                input_file=args["input_file"],
                creds_file=args["creds_file"],
                total=args["total"],
                headless=args["headless"],
                controller=self.controller,
                # Pass extra advanced args to main wrapper -> leads scrubbing
                sheet_behavior=args["sheet_behavior"],
                max_scroll_time=args["max_scroll_time"]
            )
            
            print("--- PROCESS FINISHED ---")
 
        except Exception as e:
            print(f"CRITICAL GUI THREAD ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            self.after(0, self.reset_ui_state)
 
    def reset_ui_state(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_pause.configure(state="disabled")
        self.btn_skip.configure(state="disabled")
        self.btn_pause.configure(text="PAUSE", fg_color="#FFA500")
 
if __name__ == "__main__":
    # CHECK FOR INSTALL MODE (For Frozen Executable Recursion)
    if "--install-browsers" in sys.argv:
        try:
            # We are in the subprocess. Run install logic.
            # We use the python that is running this (sys.executable) to run the module
            # But wait, in frozen mode, sys.executable IS the app.
            # So we can't run "python -m playwright".
            # We must use the playwright python API directly.
            
            print("--- DATA INSTALLATION MODE ---")
            from playwright.main import main
            sys.argv = ["playwright", "install", "chromium"]
            sys.exit(main())
        except Exception as e:
            print(f"INSTALL ERROR: {e}")
            sys.exit(1)

    app = ScraperGUI()
    app.mainloop()

