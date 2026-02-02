"""
SPDX-License-Identifier: GPL-3.0-or-later

Copyright (C) 2026 Al Gelders

This file is part of the SAR Dog Training Logger

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
Combined UI Module for SAR Dog Training Logger
Integrates both Air-Scenting and Trailing training session entry
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkcalendar import DateEntry
import json
import os
import re
from pathlib import Path
from datetime import datetime
from getpass import getuser
from config import CONFIG_FILE, BOOTSTRAP_FILE
from splash_screen import SplashScreen
from ui_file_operations import FileOperations
from ui_misc2 import Misc2Operations
from setup_tab import SetupTab
from ui_form_management import FormManagement
from ui_navigation import Navigation
from ui_database import DatabaseOperations, get_db_manager
from about_dialog import show_about
from tips import ToolTip, ConditionalToolTip
from ui_utils import get_username, get_default_terrain_types, get_default_distraction_types, save_json_mirrored
from ui_misc_data_ops import MiscDataOperations
from working_dialog import WorkingDialog, run_with_working_dialog
import sv

# Combined app constants
APP_TITLE = "SAR Dog Training Logger"
APP_VERSION = "1.0.11-alpha"
GITHUB_URL = "github.com/agelders2021/sar-dog-training-logger"


class TrainingLoggerUI:
    """Main UI class for Combined SAR Dog Training Logger (Air Scenting + Trailing)"""
    
    def __init__(self):
        """Initialize the UI"""
        print("DEBUG: UI init starting")
        
        # Load configuration
        self.config_file = CONFIG_FILE
        self.bootstrap_file = BOOTSTRAP_FILE
        
        # Initialize machine-specific paths
        self.machine_db_path = ""
        self.machine_trail_maps_folder = ""
        self.machine_backup_folder = ""
        self.machine_current_user = ""
        self.machine_user_list = []
        self.last_tab_index = 0  # Track last selected tab
        
        # Load paths from bootstrap if exists
        self.load_bootstrap()
        
        # CRITICAL: Update database path in the shared config module BEFORE any database operations
        import config as original_config
        if self.machine_db_path:
            db_file = Path(self.machine_db_path) / "air_scenting.db"
            original_config.DB_CONFIG["sqlite"]["url"] = f"sqlite:///{db_file}"
            try:
                from database import engine
                engine.dispose()
            except:
                pass
        
        # Load config
        self.config = self.load_config()
        
        # Create main window with drag-and-drop support
        self.root = TkinterDnD.Tk()
        
        # Initialize sv module with the root window
        sv.initialize(self.root)
        sv.db_type.set(self.config.get("db_type", "sqlite"))
        
        # Load saved password for networked databases
        if sv.db_type.get() in ["postgres", "supabase", "mysql"]:
            from password_manager import get_decrypted_password, check_crypto_available
            if check_crypto_available():
                saved_password = get_decrypted_password(self.config, sv.db_type.get())
                if saved_password:
                    sv.db_password.set(saved_password)
        
        # Load bootstrap values into sv
        sv.db_path.set(self.machine_db_path)
        sv.trail_maps_folder.set(self.machine_trail_maps_folder)
        sv.backup_folder.set(self.machine_backup_folder)
        sv.current_user.set(self.machine_current_user)
        
        # Initialize helper modules for airscenting
        self.file_ops = FileOperations(self)
        self.form_mgmt = FormManagement(self)
        self.navigation = Navigation(self)
        self.misc_data_ops = MiscDataOperations(self)
        self.misc2_ops = Misc2Operations(self)
        
        # For airscenting session navigation
        self.selected_sessions = []
        self.selected_sessions_index = -1
        
        # Geometry save control
        self._geometry_save_enabled = False
        self._geometry_save_after_id = None
        
        # Tab tracking
        self.previous_tab_index = 0
        
        # Withdraw during splash
        self.root.withdraw()
        
        # Set window properties
        self.root.title(APP_TITLE)
        
        # Window geometry handling
        window_width = 1200
        window_height = 900
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Try to restore saved geometry
        saved_geometry = self.config.get("window_geometry", None)
        geometry_restored = False
        final_geometry = None
        
        print(f"DEBUG: Attempting to restore geometry")
        print(f"DEBUG: saved_geometry from config = '{saved_geometry}'")
        print(f"DEBUG: screen dimensions = {screen_width}x{screen_height}")
        
        if saved_geometry:
            import re as re_module
            match = re_module.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', saved_geometry)
            print(f"DEBUG: regex match = {match}")
            if match:
                w, h, x, y = map(int, match.groups())
                print(f"DEBUG: parsed geometry: w={w}, h={h}, x={x}, y={y}")
                
                # Sanity check
                sanity_check = (w >= 400 and w <= screen_width + 500 and
                               h >= 300 and h <= screen_height + 200 and
                               x >= -100 and x <= screen_width + 500 and
                               y >= -100 and y <= screen_height + 200)
                print(f"DEBUG: sanity check passed = {sanity_check}")
                
                if sanity_check:
                    final_geometry = saved_geometry
                    print(f"DEBUG: Applying saved geometry: {final_geometry}")
                    geometry_restored = True
        
        if not geometry_restored:
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            final_geometry = f"{window_width}x{window_height}+{x}+{y}"
            print(f"DEBUG: Using default geometry: {final_geometry}")
        
        self.root.geometry(final_geometry)
        
        # Show splash screen
        self.splash = SplashScreen(self.root, version=APP_VERSION,
                                   app_title=APP_TITLE, github_url=GITHUB_URL,
                                   main_window_geometry=final_geometry)
        
        # Bind geometry changes
        self.root.bind("<Configure>", self._on_geometry_change)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.airscent_tab = ttk.Frame(self.notebook)
        self.trailing_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.setup_tab, text="Setup")
        self.notebook.add(self.airscent_tab, text="Air Scent Training Session")
        self.notebook.add(self.trailing_tab, text="Trailing Training Session")
        
        # Alias for backward compatibility with modules expecting entry_tab
        self.entry_tab = self.airscent_tab
        
        # Initialize SetupTab manager (shared by both)
        self.setup_tab_mgr = SetupTab(self)
        
        # Setup all tabs
        self.setup_tab_mgr.setup_setup_tab()
        self.setup_airscent_tab()
        self.setup_trailing_tab()
        
        # Restore last tab
        self.root.after(250, self.restore_last_tab)
        
        # Status bar frame at bottom (unified for both tabs)
        status_bar_frame = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create status bar widgets
        self.status_left_arrow = tk.Button(status_bar_frame, text="\u25C0",
                                           width=2, state="disabled")
        self.status_left_arrow.pack(side=tk.LEFT, padx=(2, 0))
        
        self.status_right_arrow = tk.Button(status_bar_frame, text="\u25B6",
                                            width=2, state="disabled")
        self.status_right_arrow.pack(side=tk.LEFT, padx=(2, 0))
        
        self.status_cancel_button = tk.Button(status_bar_frame, text="Cancel Msg",
                                              width=10, relief=tk.RAISED, cursor="hand2")
        self.status_cancel_button.pack(side=tk.LEFT, padx=(5, 2))
        
        # Use sv.status for unified status bar
        self.status_label = tk.Label(status_bar_frame, textvariable=sv.status,
                                     anchor=tk.W, padx=5, pady=2)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Initialize StatusBarManager
        from status_bar import StatusBarManager
        self.status_bar_mgr = StatusBarManager(
            root=self.root,
            status_var=sv.status,
            status_label=self.status_label,
            left_arrow=self.status_left_arrow,
            right_arrow=self.status_right_arrow,
            cancel_button=self.status_cancel_button
        )
        
        # Bind click on label to dismiss
        self.status_label.bind("<Button-1>", self.status_bar_mgr.dismiss_message)
        
        # Legacy flags for compatibility
        self.error_showing = False
        self.is_flashing = False
        self.flash_after_id = None
        self.status_message_history = []
        
        # Show main window
        self.root.deiconify()
        self.root.update()
        
        # Load initial data
        self.root.after(500, self.load_initial_data)
        self.root.after(700, self.load_trailing_initial_data)
        
        # Enable geometry saving after startup
        self.root.after(1000, self._enable_geometry_save)
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # =========================================================================
    # BOOTSTRAP AND CONFIG METHODS
    # =========================================================================
    
    def load_bootstrap(self):
        """Load machine-specific paths from bootstrap file."""
        self.last_tab_index = 0  # Default to Setup tab
        
        if self.bootstrap_file.exists():
            try:
                with open(self.bootstrap_file, 'r') as f:
                    bootstrap = json.load(f)
                    
                    # Load last tab index
                    self.last_tab_index = bootstrap.get("last_tab", 0)
                    
                    # Check for new multi-user format
                    if "users" in bootstrap:
                        self.machine_current_user = bootstrap.get("current_user", "")
                        self.machine_user_list = list(bootstrap.get("users", {}).keys())
                        
                        if self.machine_current_user and self.machine_current_user in bootstrap.get("users", {}):
                            user_settings = bootstrap["users"][self.machine_current_user]
                            self.machine_db_path = user_settings.get("db_file_path", "")
                            self.machine_trail_maps_folder = user_settings.get("trail_maps_folder", "")
                            self.machine_backup_folder = user_settings.get("backup_folder", "")
                    else:
                        # Legacy format
                        default_user = getuser()
                        self.machine_current_user = default_user
                        self.machine_user_list = [default_user]
                        self.machine_db_path = bootstrap.get("db_file_path", "")
                        self.machine_trail_maps_folder = bootstrap.get("trail_maps_folder", "")
                        self.machine_backup_folder = bootstrap.get("backup_folder", "")
            except:
                pass
        
        if not self.machine_current_user:
            self.machine_current_user = getuser()
            self.machine_user_list = [self.machine_current_user]
    
    def save_bootstrap(self):
        """Save machine-specific paths to bootstrap file."""
        bootstrap = {"current_user": "", "last_tab": 0, "users": {}}
        
        if self.bootstrap_file.exists():
            try:
                with open(self.bootstrap_file, 'r') as f:
                    existing = json.load(f)
                    if "users" in existing:
                        bootstrap = existing
                    else:
                        # Migrate legacy format
                        default_user = getuser()
                        bootstrap["current_user"] = default_user
                        bootstrap["last_tab"] = existing.get("last_tab", 0)
                        bootstrap["users"][default_user] = {
                            "db_file_path": existing.get("db_file_path", ""),
                            "trail_maps_folder": existing.get("trail_maps_folder", ""),
                            "backup_folder": existing.get("backup_folder", "")
                        }
            except:
                pass
        
        if not self.machine_current_user:
            self.machine_current_user = getuser()
        
        bootstrap["current_user"] = self.machine_current_user
        bootstrap["last_tab"] = getattr(self, 'last_tab_index', 0)
        bootstrap["users"][self.machine_current_user] = {
            "db_file_path": self.machine_db_path,
            "trail_maps_folder": self.machine_trail_maps_folder,
            "backup_folder": self.machine_backup_folder
        }
        
        self.machine_user_list = list(bootstrap["users"].keys())
        
        with open(self.bootstrap_file, 'w') as f:
            json.dump(bootstrap, f, indent=2)
    
    def restore_last_tab(self):
        """Restore the last selected tab from bootstrap."""
        db_exists = False
        if self.machine_db_path:
            db_file = Path(self.machine_db_path) / "air_scenting.db"
            db_exists = db_file.exists()
        
        if not db_exists:
            self.notebook.select(self.setup_tab)
            self.previous_tab_index = 0
            self.last_tab_index = 0
            print("No database found - starting on Setup tab")
            return
        
        last_tab = getattr(self, 'last_tab_index', 0)
        if last_tab < 0 or last_tab > 2:
            last_tab = 1
        
        if last_tab == 0:
            self.notebook.select(self.setup_tab)
        elif last_tab == 1:
            self.notebook.select(self.airscent_tab)
        elif last_tab == 2:
            self.notebook.select(self.trailing_tab)
        
        self.previous_tab_index = last_tab
        print(f"Restored to last tab: {['Setup', 'Air Scenting', 'Trailing'][last_tab]}")
    
    def load_config(self):
        """Load configuration from file or JSON folder"""
        # Try JSON folder first
        if self.machine_db_path:
            json_folder = Path(self.machine_db_path) / "JSON"
            json_config = json_folder / ".training_log_config.json"
            if json_config.exists():
                try:
                    with open(json_config, 'r') as f:
                        print(f"Loaded config from JSON folder: {json_config}")
                        return json.load(f)
                except:
                    pass
        
        # Fall back to local config file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {}
    
    def save_config(self, mirror_to_secondary=True):
        """Save configuration to file"""
        # Ensure airscenting section exists for window geometry
        if "airscenting" not in self.config:
            self.config["airscenting"] = {}
        
        # Save to JSON folder if available
        if self.machine_db_path:
            json_folder = Path(self.machine_db_path) / "JSON"
            if json_folder.exists():
                json_config = json_folder / ".training_log_config.json"
                try:
                    with open(json_config, 'w') as f:
                        json.dump(self.config, f, indent=2)
                    
                    # Mirror to secondary backup
                    if mirror_to_secondary and self.machine_backup_folder:
                        secondary_json = Path(self.machine_backup_folder) / "JSON"
                        if secondary_json.exists():
                            secondary_config = secondary_json / ".training_log_config.json"
                            try:
                                with open(secondary_config, 'w') as f:
                                    json.dump(self.config, f, indent=2)
                                print(f"Config mirrored to secondary: {secondary_config}")
                            except Exception as e:
                                print(f"Warning: Could not mirror config to secondary: {e}")
                except Exception as e:
                    print(f"Error saving config to JSON folder: {e}")
        
        # Also save to local config
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving local config: {e}")
    
    def get_json_config_path(self):
        """Get the path to config file in JSON folder"""
        if self.machine_db_path:
            json_folder = Path(self.machine_db_path) / "JSON"
            if json_folder.exists():
                return json_folder / ".training_log_config.json"
        return None
    
    # =========================================================================
    # MENU AND UI HELPERS
    # =========================================================================
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_dialog)
    
    def show_about_dialog(self):
        """Show the About dialog"""
        show_about(self.root, version=APP_VERSION,
                   app_title=APP_TITLE, github_url="https://" + GITHUB_URL)
    
    def show_status_message(self, message, msg_type="info"):
        """Show a message in the status bar - unified for all tabs"""
        sv.status.set(message)
        
        if hasattr(self, 'status_bar_mgr'):
            self.status_bar_mgr.show_message(message, msg_type)
    
    def on_closing(self):
        """Handle window close event"""
        # Check for unsaved changes in airscenting
        if hasattr(self, 'form_mgmt') and not self.form_mgmt.check_unsaved_changes("quit"):
            return
        
        # Check for unsaved changes in trailing
        if hasattr(self, 'trailing_entry') and hasattr(self.trailing_entry, 'has_unsaved_changes'):
            if self.trailing_entry.has_unsaved_changes():
                result = messagebox.askyesnocancel(
                    "Unsaved Changes",
                    "You have unsaved changes in the Trailing tab. Save before closing?",
                    icon='warning'
                )
                if result is None:  # Cancel
                    return
                elif result:  # Yes - save
                    self.trailing_entry._save_session()
        
        self.root.destroy()
    
    # =========================================================================
    # TAB CHANGE HANDLING
    # =========================================================================
    
    def on_tab_changed(self, event):
        """Handle tab change event"""
        current_tab_index = self.notebook.index(self.notebook.select())
        
        # Check if leaving Setup tab
        if self.previous_tab_index == 0 and current_tab_index != 0:
            if not self.check_setup_requirements():
                self.notebook.select(self.setup_tab)
                self.previous_tab_index = 0
                return
            
            if not self.form_mgmt.check_unsaved_changes("switch tabs"):
                self.notebook.select(self.setup_tab)
                self.previous_tab_index = 0
                return
            
            # Ensure password is set for networked databases
            db_type = sv.db_type.get()
            if db_type in ["postgres", "supabase", "mysql"]:
                password = sv.db_password.get().strip()
                if password:
                    self.set_db_password()
                
                working_dialog = WorkingDialog(self.root, "Loading Session",
                                             "Loading Training Session tab...")
                self.root.update()
                self.root.after(300, lambda: working_dialog.close(delay_ms=200))
        
        self.previous_tab_index = current_tab_index
        self.last_tab_index = current_tab_index
        self.save_bootstrap()
    
    def check_setup_requirements(self):
        """Check if database and required folders are configured"""
        db_type = sv.db_type.get()
        
        if db_type == "sqlite":
            db_path = sv.db_path.get().strip()
            if not db_path:
                messagebox.showwarning(
                    "Setup Required",
                    "Please set the Database Folder before using the training session tabs."
                )
                return False
            
            db_file = Path(db_path) / "air_scenting.db"
            if not db_file.exists():
                messagebox.showwarning(
                    "Database Required",
                    "Please initialize data structures before using the training session tabs."
                )
                return False
        
        backup_folder = sv.backup_folder.get().strip()
        trail_maps_folder = sv.trail_maps_folder.get().strip()
        
        if not backup_folder or not trail_maps_folder:
            messagebox.showwarning(
                "Setup Required",
                "Please set both the Backup Folder and Trail Maps Folder before using the training session tabs."
            )
            return False
        
        print(f"  backup_folder = '{backup_folder}'")
        print(f"  trail_maps_folder = '{trail_maps_folder}'")
        print(f"  backup exists on disk: {Path(backup_folder).exists()}")
        print(f"  trail_maps exists on disk: {Path(trail_maps_folder).exists()}")
        
        return True
    
    def set_db_password(self):
        """Set database password for networked database"""
        from database import set_db_password as db_set_password
        db_set_password(sv.db_password.get())
    
    # =========================================================================
    # GEOMETRY HANDLING
    # =========================================================================
    
    def _on_geometry_change(self, event):
        """Handle window geometry changes"""
        if not self._geometry_save_enabled:
            return
        if event.widget != self.root:
            return
        
        if self._geometry_save_after_id:
            self.root.after_cancel(self._geometry_save_after_id)
        
        self._geometry_save_after_id = self.root.after(500, self._save_window_geometry)
    
    def _enable_geometry_save(self):
        """Enable geometry saving after startup"""
        self._geometry_save_enabled = True
        print("DEBUG: Geometry saving now enabled")
    
    def _save_window_geometry(self):
        """Save current window geometry to config"""
        try:
            if os.name == 'nt':
                if self.root.state() == 'zoomed':
                    print("DEBUG: Window is zoomed, skipping geometry save")
                    return
            else:
                try:
                    if self.root.attributes('-zoomed'):
                        print("DEBUG: Window is zoomed, skipping geometry save")
                        return
                except:
                    pass
            
            geometry = self.root.geometry()
            self.config["window_geometry"] = geometry
            
            json_path = self.get_json_config_path()
            print(f"DEBUG: Saving geometry '{geometry}'")
            print(f"DEBUG: machine_db_path = '{self.machine_db_path}'")
            print(f"DEBUG: json_config_path = {json_path}")
            
            self.save_config()
        except Exception as e:
            import traceback
            print(f"Error saving window geometry: {e}")
            traceback.print_exc()


    # =========================================================================
    # AIR SCENTING TAB SETUP
    # =========================================================================
    
    def setup_airscent_tab(self):
        """Setup the Air Scenting Training Session Entry tab"""
        # Create scrollable frame
        canvas = tk.Canvas(self.airscent_tab)
        scrollbar = ttk.Scrollbar(self.airscent_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Session Information Frame
        session_frame = tk.LabelFrame(scrollable_frame, text="Session Information", padx=10, pady=5)
        session_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        # Row 0: Date and Session Number
        tk.Label(session_frame, text="Date:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.a_date_picker = DateEntry(session_frame, width=12, background='darkblue',
                                       foreground='white', borderwidth=2,
                                       date_pattern='yyyy-mm-dd')
        self.a_date_picker.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.a_date_picker.bind("<<DateEntrySelected>>", self._on_airscent_date_changed)
        
        tk.Label(session_frame, text="Session #:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.a_session_entry = tk.Entry(session_frame, textvariable=sv.session_number, width=10)
        self.a_session_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Button(session_frame, text="New", command=self._new_airscent_session).grid(row=0, column=4, padx=5)
        
        self.a_view_edit_hide_btn = tk.Button(session_frame, text="View/Edit/Hide Prior Session(s)",
                                              command=self.navigation.load_prior_session,
                                              bg="#4169E1", fg="white")
        self.a_view_edit_hide_btn.grid(row=0, column=5, sticky='e', padx=5, pady=2)
        
        # Navigation buttons
        self.a_prev_session_btn = tk.Button(session_frame, text="\u25C0 Previous", bg="#FF8C00", fg="white",
                                           width=10, command=self.navigation.navigate_previous_session, state=tk.DISABLED)
        self.a_prev_session_btn.grid(row=0, column=6, padx=2, pady=2)
        
        self.a_next_session_btn = tk.Button(session_frame, text="Next \u25B6", bg="#FF8C00", fg="white",
                                           width=10, command=self.navigation.navigate_next_session, state=tk.DISABLED)
        self.a_next_session_btn.grid(row=0, column=7, padx=2, pady=2)
        
        # Row 1: Handler and Purpose
        tk.Label(session_frame, text="Handler:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.a_handler_entry = tk.Entry(session_frame, textvariable=sv.handler, width=15)
        self.a_handler_entry.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Add Session Purpose:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.a_purpose_combo = ttk.Combobox(session_frame, textvariable=sv.a_purpose, width=16,
                                           values=['Area Search', 'Article Search', 'Water Search',
                                                  'Cadaver', 'Motivational', 'Obedience',
                                                  'Mock Cert Test', 'Mission'])
        self.a_purpose_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        self.a_purpose_combo.bind('<<ComboboxSelected>>', self._add_to_airscent_purpose_list)
        self.a_purpose_combo.bind('<Return>', self._add_to_airscent_purpose_list)
        
        # Purpose listbox
        purpose_list_frame = tk.Frame(session_frame)
        purpose_list_frame.grid(row=1, column=4, rowspan=2, columnspan=2, sticky="w", padx=5, pady=2)
        tk.Label(purpose_list_frame, text="Session Purposes:").pack(side=tk.LEFT, padx=(0, 5))
        self.a_purpose_listbox = tk.Listbox(purpose_list_frame, height=3, width=25)
        self.a_purpose_listbox.pack(side=tk.LEFT)
        self.a_purpose_listbox.bind('<Double-Button-1>', self._remove_airscent_purpose)
        
        # Row 2: Field Support and Dog
        tk.Label(session_frame, text="Field Support:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.a_field_support_entry = tk.Entry(session_frame, textvariable=sv.field_support, width=15)
        self.a_field_support_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Dog:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        self.a_dog_combo = ttk.Combobox(session_frame, textvariable=sv.dog, width=16, state="readonly")
        self.a_dog_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
        self.a_dog_combo.bind('<<ComboboxSelected>>', self._on_airscent_dog_changed)
        
        # Search Parameters Frame
        search_frame = tk.LabelFrame(scrollable_frame, text="Search Parameters", padx=10, pady=5)
        search_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        tk.Label(search_frame, text="Location:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.a_location_combo = ttk.Combobox(search_frame, textvariable=sv.location, width=20)
        self.a_location_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Search Area Size:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.a_search_area_combo = ttk.Combobox(search_frame, textvariable=sv.search_area_size, width=12,
                                               values=['Small', 'Medium', 'Large', 'Very Large'])
        self.a_search_area_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="# Subjects:").grid(row=0, column=4, sticky="w", padx=5, pady=2)
        self.a_num_subjects_combo = ttk.Combobox(search_frame, textvariable=sv.num_subjects, width=5,
                                                values=['0', '1', '2', '3', '4', '5'])
        self.a_num_subjects_combo.grid(row=0, column=5, sticky="w", padx=5, pady=2)
        self.a_num_subjects_combo.bind('<<ComboboxSelected>>', self._on_num_subjects_changed)
        
        tk.Label(search_frame, text="Handler Knowledge:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.a_handler_knowledge_combo = ttk.Combobox(search_frame, textvariable=sv.handler_knowledge, width=20,
                                                     values=['Blind', 'Single Blind', 'Double Blind', 'Known'])
        self.a_handler_knowledge_combo.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Search Type:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.a_search_type_combo = ttk.Combobox(search_frame, textvariable=sv.search_type, width=12,
                                               values=['Area', 'Article', 'Water', 'Cadaver', 'Trailing'])
        self.a_search_type_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        # Weather Frame
        weather_frame = tk.LabelFrame(scrollable_frame, text="Weather Conditions", padx=10, pady=5)
        weather_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        tk.Label(weather_frame, text="Weather:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.a_weather_combo = ttk.Combobox(weather_frame, textvariable=sv.weather, width=12,
                                           values=['Clear', 'Cloudy', 'Light Rain', 'Heavy Rain',
                                                  'Windy', 'Snow', 'Fog', 'Hot/Sunny'])
        self.a_weather_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Temperature (°F):").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.a_temp_entry = tk.Entry(weather_frame, textvariable=sv.temperature, width=10)
        self.a_temp_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Direction:").grid(row=0, column=4, sticky="w", padx=5, pady=2)
        self.a_wind_dir_combo = ttk.Combobox(weather_frame, textvariable=sv.wind_direction, width=8,
                                            values=['N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', 'Variable'])
        self.a_wind_dir_combo.grid(row=0, column=5, sticky="w", padx=5, pady=2)
        
        tk.Label(weather_frame, text="Wind Speed:").grid(row=0, column=6, sticky="w", padx=5, pady=2)
        self.a_wind_speed_entry = tk.Entry(weather_frame, textvariable=sv.wind_speed, width=10)
        self.a_wind_speed_entry.grid(row=0, column=7, sticky="w", padx=5, pady=2)
        
        # Terrain Frame
        terrain_frame = tk.LabelFrame(scrollable_frame, text="Terrain", padx=10, pady=5)
        terrain_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        tk.Label(terrain_frame, text="Add Terrain Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.a_terrain_combo = ttk.Combobox(terrain_frame, textvariable=sv.terrain, width=15, state="readonly")
        self.a_terrain_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.a_terrain_combo.bind('<<ComboboxSelected>>', self._add_to_airscent_terrain_list)
        
        tk.Label(terrain_frame, text="Terrain Types:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.a_terrain_listbox = tk.Listbox(terrain_frame, height=3, width=25)
        self.a_terrain_listbox.grid(row=0, column=3, rowspan=2, sticky="w", padx=5, pady=2)
        self.a_terrain_listbox.bind('<Double-Button-1>', self._remove_airscent_terrain)
        
        # Results Frame
        results_frame = tk.LabelFrame(scrollable_frame, text="Search Results", padx=10, pady=5)
        results_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        tk.Label(results_frame, text="Drive Level:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.a_drive_combo = ttk.Combobox(results_frame, textvariable=sv.drive_level, width=12,
                                         values=['Low', 'Medium', 'High', 'Very High'])
        self.a_drive_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(results_frame, text="Subjects Found:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.a_subjects_found_combo = ttk.Combobox(results_frame, textvariable=sv.subjects_found, width=5,
                                                  values=['0', '1', '2', '3', '4', '5'], state='disabled')
        self.a_subjects_found_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(results_frame, text="Start Time:").grid(row=0, column=4, sticky="w", padx=5, pady=2)
        self.a_start_time_entry = tk.Entry(results_frame, textvariable=sv.start_time, width=10)
        self.a_start_time_entry.grid(row=0, column=5, sticky="w", padx=5, pady=2)
        
        tk.Label(results_frame, text="Finish Time:").grid(row=0, column=6, sticky="w", padx=5, pady=2)
        self.a_finish_time_entry = tk.Entry(results_frame, textvariable=sv.finish_time, width=10)
        self.a_finish_time_entry.grid(row=0, column=7, sticky="w", padx=5, pady=2)
        
        # Notes Frame
        notes_frame = tk.LabelFrame(scrollable_frame, text="Notes", padx=10, pady=5)
        notes_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        self.a_notes_text = tk.Text(notes_frame, height=4, width=80)
        self.a_notes_text.pack(fill="x", expand=True, padx=5, pady=5)
        
        # Button Frame
        button_frame = tk.Frame(scrollable_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        self.a_save_session_btn = tk.Button(button_frame, text="Save Session",
                                           command=self.save_airscent_session,
                                           bg="#4CAF50", fg="white",
                                           font=("Helvetica", 12, "bold"),
                                           width=25, height=2)
        self.a_save_session_btn.pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Clear Form", command=self.form_mgmt.clear_form,
                 width=15).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Quit", command=self.on_closing,
                 width=10).pack(side="left", padx=10)
        
        # Initialize navigation button states
        self.root.after(500, self.navigation.update_navigation_buttons)
        
        # Initialize subjects_found as disabled
        self.a_subjects_found_combo['state'] = 'disabled'

    # =========================================================================
    # TRAILING TAB SETUP
    # =========================================================================
    
    def setup_trailing_tab(self):
        """Setup the Trailing Training Session Entry tab"""
        from ui_trailing import TrailingEntryTab
        
        # Create callbacks for the trailing entry tab
        callbacks = {
            'on_save': self.on_trailing_session_save,
            'get_next_session_number': self.get_trailing_next_session_number,
            'on_load_prior_session': self.on_trailing_load_prior_session,
            'on_navigate_previous': self.on_trailing_navigate_previous,
            'on_navigate_next': self.on_trailing_navigate_next,
            'on_export_pdf': self.on_trailing_export_pdf,
            'on_resume_session': self.on_trailing_resume_session,
            'on_hide_session': self.on_trailing_hide_session,
        }
        
        # Create the trailing entry tab
        self.trailing_entry = TrailingEntryTab(self.trailing_tab, self, callbacks)
    
    # =========================================================================
    # INITIAL DATA LOADING
    # =========================================================================
    
    def load_initial_data(self):
        """Load initial data for airscenting tab"""
        try:
            # Load dogs
            db_mgr = get_db_manager(sv.db_type.get())
            dog_names = db_mgr.load_dog_names()
            self.a_dog_combo['values'] = dog_names
            
            # Load locations
            locations = db_mgr.load_training_locations()
            self.a_location_combo['values'] = sorted(locations) if locations else []
            
            # Load terrain types
            terrain_types = self.get_terrain_types()
            self.a_terrain_combo['values'] = terrain_types
            
            # Set default handler
            airscent_config = self.config.get("airscenting", {})
            default_handler = airscent_config.get("default_handler", "")
            if default_handler:
                sv.handler.set(default_handler)
            
            # Set last dog
            last_dog = airscent_config.get("last_dog", "")
            if last_dog and last_dog in dog_names:
                sv.dog.set(last_dog)
                self._update_airscent_session_number()
            
            # Take form snapshot
            if hasattr(self, 'form_mgmt'):
                self.form_mgmt.take_form_snapshot()
            
            sv.status.set("Ready")
            print("Database valid - starting on Entry tab")
            
        except Exception as e:
            print(f"Error loading initial data: {e}")
            import traceback
            traceback.print_exc()
    
    def load_trailing_initial_data(self):
        """Load initial data for the trailing tab"""
        try:
            # Load dog names
            dog_names = self.get_dog_names()
            print(f"DEBUG: Trailing - loaded {len(dog_names)} dogs")
            self.trailing_entry.update_dog_list(dog_names)
            
            # Load locations
            locations = self.get_training_locations()
            print(f"DEBUG: Trailing - loaded {len(locations)} locations")
            self.trailing_entry.update_location_list(locations)
            
            # Load terrain types
            terrain_types = self.get_terrain_types()
            print(f"DEBUG: Trailing - loaded {len(terrain_types)} terrain types: {terrain_types}")
            self.trailing_entry.update_terrain_types(terrain_types)
            
            # Load distraction types
            distraction_types = self.get_distraction_types()
            print(f"DEBUG: Trailing - loaded {len(distraction_types)} distraction types")
            self.trailing_entry.update_distraction_types(distraction_types)
            
            # Set default handler from config
            trailing_config = self.config.get("trailing", {})
            default_handler = trailing_config.get("default_handler", "")
            if default_handler:
                sv.t_handler.set(default_handler)
            
            # Set last dog from config
            last_dog = trailing_config.get("last_dog", "")
            if last_dog and last_dog in dog_names:
                sv.t_dog.set(last_dog)
                try:
                    next_session = self.get_trailing_next_session_number(last_dog)
                    sv.t_session.set(str(next_session))
                except Exception as e:
                    print(f"Error getting next session number: {e}")
            
            # Take form snapshot after data is loaded
            if hasattr(self, 'trailing_entry'):
                self.trailing_entry.take_form_snapshot()
                
        except Exception as e:
            print(f"Error loading trailing initial data: {e}")
            import traceback
            traceback.print_exc()
    
    # =========================================================================
    # CONFIG PROVIDER METHODS (used by trailing tab)
    # =========================================================================
    
    def get_handler_name(self):
        """Get the default handler name"""
        return self.config.get("trailing", {}).get("default_handler", "")
    
    def get_dog_names(self):
        """Get list of dog names from database"""
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            return db_mgr.load_dog_names()
        except:
            return self.config.get("dog_names", [])
    
    def get_last_dog_name(self):
        """Get the last used dog name"""
        return self.config.get("trailing", {}).get("last_dog", "")
    
    def get_terrain_types(self):
        """Get terrain types from database, with fallback to defaults"""
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            terrain_types = db_mgr.load_terrain_types()
            
            if not terrain_types:
                terrain_types = self.config.get("terrain_types", [])
            
            if not terrain_types:
                terrain_types = get_default_terrain_types()
            
            return terrain_types
        except Exception as e:
            print(f"Error loading terrain types: {e}")
            terrain_types = self.config.get("terrain_types", [])
            if not terrain_types:
                terrain_types = get_default_terrain_types()
            return terrain_types
    
    def get_distraction_types(self):
        """Get distraction types from database, with fallback to defaults"""
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            distraction_types = db_mgr.load_distraction_types()
            
            if not distraction_types:
                distraction_types = self.config.get("distraction_types", [])
            
            if not distraction_types:
                distraction_types = get_default_distraction_types()
            
            return distraction_types
        except Exception as e:
            print(f"Error loading distraction types: {e}")
            distraction_types = self.config.get("distraction_types", [])
            if not distraction_types:
                distraction_types = get_default_distraction_types()
            return distraction_types
    
    def get_training_locations(self):
        """Get training locations from database"""
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            return db_mgr.load_training_locations()
        except:
            return self.config.get("training_locations", [])

    # =========================================================================
    # AIR SCENTING HELPER METHODS
    # =========================================================================
    
    def _on_airscent_date_changed(self, event=None):
        """Handle date change in airscenting tab"""
        date_str = self.a_date_picker.get_date().strftime("%Y-%m-%d")
        sv.date.set(date_str)
    
    def _new_airscent_session(self):
        """Start a new airscenting session"""
        self.form_mgmt.clear_form()
        self._update_airscent_session_number()
    
    def _update_airscent_session_number(self):
        """Update session number for current dog"""
        dog_name = sv.dog.get()
        if dog_name:
            db_ops = DatabaseOperations(self)
            next_session = db_ops.get_next_session_number(dog_name)
            sv.session_number.set(str(next_session))
            print(f"DEBUG: About to schedule update_initial_session, current dog={dog_name}, session={next_session}")
    
    def _on_airscent_dog_changed(self, event=None):
        """Handle dog selection change in airscenting"""
        self._update_airscent_session_number()
    
    def _add_to_airscent_purpose_list(self, event=None):
        """Add purpose to the accumulator list"""
        purpose = sv.a_purpose.get().strip()
        if purpose:
            current_items = list(self.a_purpose_listbox.get(0, tk.END))
            if purpose not in current_items:
                self.a_purpose_listbox.insert(tk.END, purpose)
            sv.a_purpose.set("")
    
    def _remove_airscent_purpose(self, event=None):
        """Remove purpose from list on double-click"""
        selection = self.a_purpose_listbox.curselection()
        if selection:
            self.a_purpose_listbox.delete(selection[0])
    
    def _add_to_airscent_terrain_list(self, event=None):
        """Add terrain to the accumulator list"""
        terrain = sv.terrain.get().strip()
        if terrain:
            current_items = list(self.a_terrain_listbox.get(0, tk.END))
            if terrain not in current_items:
                self.a_terrain_listbox.insert(tk.END, terrain)
            else:
                self.show_status_message(f"'{terrain}' is already in the list", "info")
            sv.terrain.set("")
    
    def _remove_airscent_terrain(self, event=None):
        """Remove terrain from list on double-click"""
        selection = self.a_terrain_listbox.curselection()
        if selection:
            self.a_terrain_listbox.delete(selection[0])
    
    def _on_num_subjects_changed(self, event=None):
        """Handle number of subjects change"""
        num = sv.num_subjects.get()
        if num and int(num) > 0:
            self.a_subjects_found_combo['state'] = 'readonly'
            self.a_subjects_found_combo['values'] = [str(i) for i in range(int(num) + 1)]
        else:
            self.a_subjects_found_combo['state'] = 'disabled'
            sv.subjects_found.set("")
    
    def save_airscent_session(self):
        """Save the airscenting session"""
        # Validate required fields
        if not sv.dog.get():
            self.show_status_message("No Dog Selected", "warning")
            return
        
        # Collect session data
        session_data = {
            'date': sv.date.get(),
            'session_number': sv.session_number.get(),
            'handler': sv.handler.get(),
            'dog_name': sv.dog.get(),
            'field_support': sv.field_support.get(),
            'location': sv.location.get(),
            'search_area_size': sv.search_area_size.get(),
            'num_subjects': sv.num_subjects.get(),
            'handler_knowledge': sv.handler_knowledge.get(),
            'search_type': sv.search_type.get(),
            'weather': sv.weather.get(),
            'temperature': sv.temperature.get(),
            'wind_direction': sv.wind_direction.get(),
            'wind_speed': sv.wind_speed.get(),
            'drive_level': sv.drive_level.get(),
            'subjects_found': sv.subjects_found.get(),
            'start_time': sv.start_time.get(),
            'finish_time': sv.finish_time.get(),
            'notes': self.a_notes_text.get("1.0", tk.END).strip(),
        }
        
        # Get terrains and purposes from listboxes
        terrains = list(self.a_terrain_listbox.get(0, tk.END))
        purposes = list(self.a_purpose_listbox.get(0, tk.END))
        
        # Save to database
        db_ops = DatabaseOperations(self)
        success, session_id, message = db_ops.save_session(session_data)
        
        if success:
            # Save terrains
            if session_id:
                db_ops.save_selected_terrains(session_id, terrains)
                db_ops.save_selected_purposes(session_id, purposes)
            
            # Save to JSON backup
            self._save_airscent_session_to_json(session_data, terrains, purposes)
            
            # Update config with last handler/dog
            if "airscenting" not in self.config:
                self.config["airscenting"] = {}
            self.config["airscenting"]["default_handler"] = sv.handler.get()
            self.config["airscenting"]["last_dog"] = sv.dog.get()
            self.save_config()
            
            # Clear form for next session
            self.form_mgmt.clear_form()
            self._update_airscent_session_number()
            
            self.show_status_message(message, "info")
        else:
            self.show_status_message(f"Error: {message}", "error")
    
    def _save_airscent_session_to_json(self, session_data, terrains, purposes):
        """Save airscenting session to JSON backup"""
        try:
            user_name = get_username()
            
            backup_data = {
                **session_data,
                "selected_terrains": terrains,
                "selected_purposes": purposes,
                "user_name": user_name,
                "update_time": datetime.now().isoformat()
            }
            
            dog_name = session_data.get('dog_name', 'unknown')
            session_num = session_data.get('session_number', '0')
            
            safe_user_name = re.sub(r'[^\w\-]', '_', user_name) if user_name else 'unknown'
            safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
            
            filename = f"a_{safe_user_name}_{safe_dog_name}_{session_num}.json"
            
            primary, secondary, checksum, primary_ts, secondary_ts = save_json_mirrored(filename, backup_data)
            
            if primary:
                print(f"Airscenting session saved to JSON: {primary}")
            if secondary:
                print(f"Airscenting session mirrored to: {secondary}")
                
        except Exception as e:
            print(f"Warning: Failed to save airscenting session to JSON: {e}")
            self.show_status_message(f"Backup failed: {str(e)}", "error")
    
    def initialize_entry_tab_data(self):
        """Load all database data for Entry tab - called after password is loaded"""
        db_mgr = get_db_manager(sv.db_type.get())
        terrain_types = db_mgr.load_terrain_types()
        if hasattr(self, 'a_terrain_combo'):
            self.a_terrain_combo['values'] = terrain_types

    # =========================================================================
    # TRAILING TAB CALLBACKS
    # =========================================================================
    
    def on_trailing_session_save(self, session_data):
        """Handle trailing session save from entry tab"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        db_ops = TDatabaseOperations(self)
        
        is_update = hasattr(self.trailing_entry, 'editing_session') and self.trailing_entry.editing_session
        
        success, session_id, message = db_ops.save_session(session_data, is_update)
        
        if success:
            if session_id:
                # Save terrains from listbox
                terrains = list(self.trailing_entry.terrain_listbox.get(0, tk.END))
                db_ops.save_selected_terrains(session_id, terrains)
                
                # Save purposes from listbox
                purposes = list(self.trailing_entry.purpose_listbox.get(0, tk.END))
                db_ops.save_selected_purposes(session_id, purposes)
                
                # Save distractions from treeview
                distractions = []
                for item in self.trailing_entry.distraction_tree.get_children():
                    values = self.trailing_entry.distraction_tree.item(item, 'values')
                    if len(values) >= 2:
                        distractions.append({
                            "type": values[0],
                            "response": values[1]
                        })
                db_ops.save_distractions(session_id, distractions)
                
                # Save to JSON backup
                self._save_trailing_session_to_json(session_data, terrains, purposes, distractions)
            
            # Clear form and prepare for next session
            self.trailing_entry.clear_form()
            
            # Save last handler and dog to config
            current_handler = sv.t_handler.get()
            current_dog = sv.t_dog.get()
            if "trailing" not in self.config:
                self.config["trailing"] = {}
            if current_handler:
                self.config["trailing"]["default_handler"] = current_handler
            if current_dog:
                self.config["trailing"]["last_dog"] = current_dog
            self.save_config()
            
            self.show_status_message(message, "info")
            return True
        else:
            print(f"ERROR saving trailing session: {message}")
            self.show_status_message(f"Error: {message}", "error")
            return False
    
    def _save_trailing_session_to_json(self, session_data, terrains, purposes, distractions):
        """Save trailing session to JSON backup file."""
        try:
            user_name = get_username()
            
            backup_data = {
                **session_data,
                "selected_terrains": terrains,
                "selected_purposes": purposes,
                "distractions": distractions,
                "user_name": user_name,
                "update_time": datetime.now().isoformat()
            }
            
            dog_name = session_data.get('t_dog_name', 'unknown')
            session_num = session_data.get('t_session_number', '0')
            
            safe_user_name = re.sub(r'[^\w\-]', '_', user_name) if user_name else 'unknown'
            safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
            
            filename = f"t_{safe_user_name}_{safe_dog_name}_{session_num}.json"
            
            primary, secondary, checksum, primary_ts, secondary_ts = save_json_mirrored(filename, backup_data)
            
            if primary:
                print(f"Trailing session saved to JSON: {primary}")
            if secondary:
                print(f"Trailing session mirrored to: {secondary}")
                
        except Exception as e:
            print(f"Warning: Failed to save trailing session to JSON: {e}")
            self.show_status_message(f"Backup failed: {str(e)}", "error")
    
    def get_trailing_next_session_number(self, dog_name):
        """Get next session number for a dog in trailing"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        db_ops = TDatabaseOperations(self)
        return db_ops.get_next_session_number(dog_name)
    
    def on_trailing_load_prior_session(self):
        """Open dialog to view/edit/hide prior trailing sessions"""
        from tkinter import Toplevel, Listbox, Scrollbar
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        if sv.sync_in_progress:
            messagebox.showinfo("Sync In Progress",
                "Please wait - background sync is in progress.")
            return
        
        dog_name = sv.t_dog.get()
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first.")
            return
        
        db_ops = TDatabaseOperations(self)
        status_filter = sv.t_session_status_filter.get()
        sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter=status_filter.capitalize())
        
        if not sessions:
            messagebox.showinfo("No Sessions", f"No trailing sessions found for {dog_name}")
            return
        
        # Create selection dialog
        dialog = Toplevel(self.root)
        dialog.title("Select Trailing Sessions to View/Edit/Hide")
        dialog.geometry("650x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        instructions = tk.Label(dialog,
            text="Select sessions to navigate:\n"
                 "• Click to select one session\n"
                 "• Ctrl+Click to select multiple sessions\n"
                 "• Shift+Click to select a range",
            justify="left", padx=10, pady=10)
        instructions.pack()
        
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        session_listbox = Listbox(list_frame, selectmode="extended", yscrollcommand=scrollbar.set,
                                  font=("Courier", 10), width=70)
        session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=session_listbox.yview)
        
        session_data_list = []
        
        def populate_listbox(sessions_to_show):
            session_listbox.delete(0, tk.END)
            session_data_list.clear()
            
            for session in sessions_to_show:
                session_num = session.get('t_session_number', '?')
                date = session.get('t_date', '')
                handler = session.get('t_handler', '') or ''
                location = session.get('t_location', '') or ''
                status = session.get('status', 'active')
                status_marker = " [HIDDEN]" if status == 'deleted' else ""
                
                display_text = f"#{session_num:3d}  |  {str(date):10s}  |  {handler:15s}  |  {location:20s}{status_marker}"
                session_listbox.insert(tk.END, display_text)
                session_data_list.append(session)
        
        populate_listbox(sessions)
        self.trailing_entry.dog_sessions_list = sessions
        
        def refresh_sessions():
            status_filter = sv.t_session_status_filter.get()
            new_sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter=status_filter.capitalize())
            populate_listbox(new_sessions)
            self.trailing_entry.dog_sessions_list = new_sessions
            
            if status_filter == 'deleted':
                delete_button.config(text="Restore Selected", bg="#28a745")
            else:
                delete_button.config(text="Hide Selected", bg="#DC143C")
        
        filter_frame = tk.Frame(dialog)
        filter_frame.pack(pady=(5, 0))
        
        tk.Label(filter_frame, text="Show Sessions:").pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(filter_frame, text="Active", variable=sv.t_session_status_filter,
                      value="active", command=refresh_sessions).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(filter_frame, text="Hidden", variable=sv.t_session_status_filter,
                      value="deleted", command=refresh_sessions).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(filter_frame, text="Both", variable=sv.t_session_status_filter,
                      value="all", command=refresh_sessions).pack(side=tk.LEFT, padx=5)
        
        def view_selected():
            selected_indices = session_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            selected_sessions = [session_data_list[i] for i in selected_indices]
            self.trailing_entry.dog_sessions_list = selected_sessions
            self.trailing_entry.current_session_index = 0
            
            self._load_trailing_session_into_form(selected_sessions[0])
            self._update_trailing_navigation_buttons()
            
            dialog.destroy()
            self.show_status_message(f"Viewing {len(selected_sessions)} selected trailing session(s)", "info")
        
        def delete_restore_selected():
            selected_indices = session_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            selected_sessions = [session_data_list[i] for i in selected_indices]
            selected_nums = [s.get('t_session_number') for s in selected_sessions]
            status_filter = sv.t_session_status_filter.get()
            
            if status_filter == 'deleted':
                result = messagebox.askyesno("Confirm Restore",
                    f"Restore {len(selected_nums)} session(s) to active?\n\nSessions: {', '.join(map(str, selected_nums))}",
                    icon='question')
                if result:
                    for session_num in selected_nums:
                        db_ops.update_session_status(session_num, dog_name, 'active')
                    self.show_status_message(f"Restored {len(selected_nums)} trailing session(s)", "info")
                    dialog.destroy()
            else:
                result = messagebox.askyesno("Confirm Hide",
                    f"Mark {len(selected_nums)} session(s) as hidden?\n\nSessions: {', '.join(map(str, selected_nums))}",
                    icon='warning')
                if result:
                    for session_num in selected_nums:
                        db_ops.update_session_status(session_num, dog_name, 'deleted')
                    self.show_status_message(f"Hidden {len(selected_nums)} trailing session(s)", "info")
                    dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="View Selected", command=view_selected,
                  bg="#4169E1", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        status_filter = sv.t_session_status_filter.get()
        button_text = "Restore Selected" if status_filter == 'deleted' else "Hide Selected"
        button_color = "#28a745" if status_filter == 'deleted' else "#DC143C"
        
        delete_button = tk.Button(btn_frame, text=button_text, command=delete_restore_selected,
                                   bg=button_color, fg="white", width=15)
        delete_button.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        session_listbox.bind('<Double-Button-1>', lambda e: view_selected())
    
    def _load_trailing_session_into_form(self, session_data):
        """Load trailing session data into the form for editing"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        self.trailing_entry.set_session_data(session_data)
        self.trailing_entry.editing_session = True
        self.trailing_entry.editing_row = session_data.get('id')
        self.trailing_entry.update_save_button_text()
        
        session_id = session_data.get('id')
        if session_id:
            db_ops = TDatabaseOperations(self)
            
            terrains = db_ops.load_selected_terrains(session_id)
            self.trailing_entry.set_selected_terrains(terrains)
            
            purposes = db_ops.load_selected_purposes(session_id)
            self.trailing_entry.set_selected_purposes(purposes)
            
            distractions = db_ops.load_distractions(session_id)
            self.trailing_entry.set_distractions(distractions)
        
        session_status = session_data.get('status', 'active')
        if session_status == 'deleted':
            if hasattr(self.trailing_entry, 'hide_btn'):
                self.trailing_entry.hide_btn.config(state=tk.DISABLED)
            if hasattr(self.trailing_entry, 'resume_btn'):
                self.trailing_entry.resume_btn.config(state=tk.NORMAL)
        else:
            if hasattr(self.trailing_entry, 'hide_btn'):
                self.trailing_entry.hide_btn.config(state=tk.NORMAL)
            if hasattr(self.trailing_entry, 'resume_btn'):
                self.trailing_entry.resume_btn.config(state=tk.DISABLED)
        
        self.show_status_message(f"Loaded trailing session {session_data.get('t_session_number')} for editing", "info")
    
    def _update_trailing_navigation_buttons(self):
        """Update prev/next button states for trailing"""
        if not self.trailing_entry.dog_sessions_list:
            self.trailing_entry.prev_session_btn.config(state=tk.DISABLED)
            self.trailing_entry.next_session_btn.config(state=tk.DISABLED)
            return
        
        idx = self.trailing_entry.current_session_index
        max_idx = len(self.trailing_entry.dog_sessions_list) - 1
        
        self.trailing_entry.prev_session_btn.config(state=tk.NORMAL if idx > 0 else tk.DISABLED)
        self.trailing_entry.next_session_btn.config(state=tk.NORMAL if idx < max_idx else tk.DISABLED)
    
    def on_trailing_navigate_previous(self):
        """Navigate to previous trailing session"""
        if not self.trailing_entry.dog_sessions_list:
            return
        
        idx = self.trailing_entry.current_session_index
        if idx > 0:
            self.trailing_entry.current_session_index = idx - 1
            session = self.trailing_entry.dog_sessions_list[idx - 1]
            self._load_trailing_session_into_form(session)
            self._update_trailing_navigation_buttons()
    
    def on_trailing_navigate_next(self):
        """Navigate to next trailing session"""
        if not self.trailing_entry.dog_sessions_list:
            return
        
        idx = self.trailing_entry.current_session_index
        max_idx = len(self.trailing_entry.dog_sessions_list) - 1
        if idx < max_idx:
            self.trailing_entry.current_session_index = idx + 1
            session = self.trailing_entry.dog_sessions_list[idx + 1]
            self._load_trailing_session_into_form(session)
            self._update_trailing_navigation_buttons()

    def on_trailing_resume_session(self):
        """Restore the currently displayed trailing session"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        if not self.trailing_entry.editing_session:
            return
        
        dog_name = sv.t_dog.get()
        session_number = sv.t_session.get()
        
        if not dog_name or not session_number:
            return
        
        try:
            session_num = int(session_number)
        except ValueError:
            return
        
        result = messagebox.askyesno("Restore Session",
            f"Mark trailing session {session_num} for {dog_name} as active?",
            icon='question')
        
        if result:
            db_ops = TDatabaseOperations(self)
            success = db_ops.update_session_status(session_num, dog_name, 'active')
            
            if success:
                self.show_status_message(f"Trailing session {session_num} restored to active", "info")
                
                for session in self.trailing_entry.dog_sessions_list:
                    if session.get('t_session_number') == session_num:
                        session['status'] = 'active'
                        break
                
                idx = self.trailing_entry.current_session_index
                if 0 <= idx < len(self.trailing_entry.dog_sessions_list):
                    self._load_trailing_session_into_form(self.trailing_entry.dog_sessions_list[idx])
            else:
                messagebox.showerror("Error", "Failed to restore trailing session")
    
    def on_trailing_hide_session(self):
        """Mark the currently displayed trailing session as hidden"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        if not self.trailing_entry.editing_session:
            return
        
        dog_name = sv.t_dog.get()
        session_number = sv.t_session.get()
        
        if not dog_name or not session_number:
            return
        
        try:
            session_num = int(session_number)
        except ValueError:
            return
        
        result = messagebox.askyesno("Hide Session",
            f"Mark trailing session {session_num} for {dog_name} as hidden?\n\nThis can be undone with the Restore button.",
            icon='warning')
        
        if result:
            db_ops = TDatabaseOperations(self)
            success = db_ops.update_session_status(session_num, dog_name, 'deleted')
            
            if success:
                self.show_status_message(f"Trailing session {session_num} marked as hidden", "info")
                
                for session in self.trailing_entry.dog_sessions_list:
                    if session.get('t_session_number') == session_num:
                        session['status'] = 'deleted'
                        break
                
                idx = self.trailing_entry.current_session_index
                if 0 <= idx < len(self.trailing_entry.dog_sessions_list):
                    self._load_trailing_session_into_form(self.trailing_entry.dog_sessions_list[idx])
            else:
                messagebox.showerror("Error", "Failed to hide trailing session")
    
    def on_trailing_export_pdf(self):
        """Export trailing sessions to PDF"""
        dog_name = sv.t_dog.get()
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first.")
            return
        
        # For now, show a message that PDF export is available
        self.show_status_message("PDF export for trailing - opening dialog...", "info")
        messagebox.showinfo("Export PDF", 
            f"PDF export for {dog_name}'s trailing sessions.\n\n"
            "This feature uses the same export dialog as the standalone trailing app.")
    
    # =========================================================================
    # RUN METHOD
    # =========================================================================
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = TrainingLoggerUI()
    app.run()
