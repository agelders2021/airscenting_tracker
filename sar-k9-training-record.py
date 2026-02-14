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
SAR Dog Training Log - Combined Application
Main entry point that integrates Area Search and Trailing training session entry.

Structure:
- sar-dog-training-log.py: Main class and startup (this file)
- air_ui.py: Area Search tab widget construction
- air_helper.py: Area Search helper methods (mixin)
- trail_ui.py: Trailing tab widget construction  
- trail_helper.py: Trailing helper methods (mixin)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import TkinterDnD
import json
import os
import re
from pathlib import Path
from datetime import datetime
from getpass import getuser

# Configuration
from config import CONFIG_FILE, BOOTSTRAP_FILE

# UI Components
from splash_screen import SplashScreen
from setup_tab import SetupTab
from about_dialog import show_about
from status_bar import StatusBarManager
from help_window import show_help_window

# Helper modules from ui.py
from ui_file_operations import FileOperations
from ui_form_management import FormManagement
from ui_navigation import Navigation
from ui_database import DatabaseOperations, get_db_manager
from ui_misc_data_ops import MiscDataOperations
from ui_misc2 import Misc2Operations
from lock_manager import LockManager

# Tab UI modules
import air_ui
import trail_ui

# Helper mixins
from air_helper import AirScentingHelper
from trail_helper import TrailingHelper

# StringVars
import sv

# App constants
APP_TITLE = "SAR K9 Training Record"
APP_VERSION = "1.0.1-alpha"
GITHUB_URL = "github.com/agelders2021/sar-k9-training-record"


class TrainingLoggerUI(AirScentingHelper, TrailingHelper):
    """
    Main UI class for Combined SAR Dog Training Logger.
    
    Inherits from:
    - AirScentingHelper: Methods for Area Search tab
    - TrailingHelper: Methods for Trailing tab
    """
    
    def __init__(self):
        """Initialize the combined UI"""
        # print(f"DEBUG: TrainingLoggerUI init starting")
        
        # Load configuration
        self.config_file = CONFIG_FILE
        self.bootstrap_file = BOOTSTRAP_FILE
        
        # Initialize machine-specific paths
        self.machine_db_path = ""
        self.machine_trail_maps_folder = ""
        self.machine_backup_folder = ""
        self.machine_pdf_folder = ""
        self.machine_excel_folder = ""
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
        sv.pdf_folder.set(self.machine_pdf_folder)
        sv.excel_folder.set(self.machine_excel_folder)
        sv.current_user.set(self.machine_current_user)
        
        # =====================================================================
        # SESSION LOCK CHECK
        # Check for an existing lock file in the secondary backup folder.
        # If another machine/user holds the lock, the user is prompted to
        # either exit immediately or take over.
        # =====================================================================
        self.lock_manager = None
        secondary_folder = self.machine_backup_folder
        if secondary_folder and Path(secondary_folder).exists():
            self.lock_manager = LockManager(self.root, secondary_folder)
            if not self.lock_manager.check_startup_lock():
                # User chose to exit ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“ tear down and abort startup
                self.root.destroy()
                import sys
                sys.exit(0)
        
        # Initialize helper modules
        self.file_ops = FileOperations(self)
        self.form_mgmt = FormManagement(self)
        self.navigation = Navigation(self)
        self.misc_data_ops = MiscDataOperations(self)
        self.misc2_ops = Misc2Operations(self)
        self.setup_tab_mgr = SetupTab(self)
        
        # For airscenting session navigation
        self.selected_sessions = []
        self.selected_sessions_index = -1
        
        # Geometry save control
        self._geometry_save_enabled = False
        self._geometry_save_after_id = None
        
        # Tab tracking
        self.previous_tab_index = 0
        self._restoring_tab = True  # Flag to prevent save during startup - set early!
        
        # Track form state for unsaved changes
        self.form_snapshot = ""
        
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
        if not saved_geometry:
            saved_geometry = self.config.get("airscenting", {}).get("window_geometry", None)
        
        geometry_restored = False
        final_geometry = None
        
        # print(f"DEBUG: Attempting to restore geometry")
        # print(f"DEBUG: saved_geometry from config = '{saved_geometry}'")
        # print(f"DEBUG: screen dimensions = {screen_width}x{screen_height}")
        
        if saved_geometry:
            match = re.match(r'(\d+)x(\d+)([+-]\d+)([+-]\d+)', saved_geometry)
            if match:
                w, h, x, y = match.groups()
                w, h, x, y = int(w), int(h), int(x), int(y)
                # print(f"DEBUG: parsed geometry: w={w}, h={h}, x={x}, y={y}")
                
                # Sanity check
                sanity_check = (w >= 400 and w <= 5000 and
                               h >= 300 and h <= 3000 and
                               x >= -2000 and x <= 10000 and
                               y >= -500 and y <= 5000)
                
                if sanity_check:
                    final_geometry = saved_geometry
                    geometry_restored = True
                    # print(f"DEBUG: Applying saved geometry: {final_geometry}")
        
        if not geometry_restored:
            x = (screen_width - window_width) // 2
            y = 0
            final_geometry = f"{window_width}x{window_height}+{x}+{y}"
            # print(f"DEBUG: Using default geometry: {final_geometry}")
        
        self.root.geometry(final_geometry)
        self.root.minsize(1024, 600)
        
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
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.airscent_tab = ttk.Frame(self.notebook)
        self.trailing_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.setup_tab, text="Setup")
        self.notebook.add(self.airscent_tab, text="Area Search Training Session")
        self.notebook.add(self.trailing_tab, text="Trailing Training Session")
        
        # Alias for backward compatibility with modules expecting entry_tab
        self.entry_tab = self.airscent_tab
        
        # Setup all tabs
        self.setup_tab_mgr.setup_setup_tab()
        air_ui.setup_airscent_tab(self)
        trail_ui.setup_trailing_tab(self)
        
        # Create status bar
        self._create_status_bar()
        
        # Show main window
        self.root.deiconify()
        self.root.update()
        
        # Schedule initial data loading
        self.root.after(500, self.misc_data_ops.load_initial_database_data)
        self.root.after(700, self.load_trailing_initial_data)
        
        # Schedule session number update
        self.root.after(600, self._update_initial_session)
        
        # Take initial form snapshot
        self.root.after(200, self.form_mgmt.take_form_snapshot)
        
        # Load last dog AFTER all data loading completes (at 1200ms to be safe)
        self.root.after(1200, self._load_last_dog_for_air_session)
        
        # Restore last tab AFTER all data loading completes
        # load_initial_database_data uses chained after(50,...) calls internally,
        # so step10 runs around 500 + (10*50) = 1000ms+ 
        # We run at 1500ms to be safe
        self.root.after(1500, self.restore_last_tab)
        
        # Enable geometry saving after startup
        self.root.after(1000, self._enable_geometry_save)
        
        # Check for and restore any inactivity snapshot from a previous forced exit
        self.root.after(2000, self._check_and_restore_inactivity_snapshot)
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind F1 key to show help window
        self.root.bind("<F1>", lambda e: show_help_window(self.root))
        
        # Start session lock activity tracking (must be after UI is built)
        if self.lock_manager:
            self.lock_manager.force_exit_callback = self._lock_force_exit
            self.lock_manager.start()
    
    # =========================================================================
    # STATUS BAR
    # =========================================================================
    
    def _create_status_bar(self):
        """Create the unified status bar at bottom of window"""
        status_bar_frame = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status bar widgets
        self.status_left_arrow = tk.Button(status_bar_frame, text="\N{BLACK LEFT-POINTING TRIANGLE}",
                                           width=2, state="disabled")
        self.status_left_arrow.pack(side=tk.LEFT, padx=(2, 0))
        
        self.status_right_arrow = tk.Button(status_bar_frame, text="\N{BLACK RIGHT-POINTING TRIANGLE}",
                                            width=2, state="disabled")
        self.status_right_arrow.pack(side=tk.LEFT, padx=(2, 0))
        
        self.status_cancel_button = tk.Button(status_bar_frame, text="Cancel Msg",
                                              width=10, relief=tk.RAISED, cursor="hand2")
        self.status_cancel_button.pack(side=tk.LEFT, padx=(5, 2))
        
        self.status_label = tk.Label(status_bar_frame, textvariable=sv.status,
                                     anchor=tk.W, padx=5, pady=2)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Initialize StatusBarManager
        self.status_bar_mgr = StatusBarManager(
            root=self.root,
            status_var=sv.status,
            status_label=self.status_label,
            left_arrow=self.status_left_arrow,
            right_arrow=self.status_right_arrow,
            cancel_button=self.status_cancel_button
        )
        
        # Register with sv module for global access from any module
        import sv as sv_module
        sv_module.set_status_bar_manager(self.status_bar_mgr)
        
        # Bind click on label to dismiss
        self.status_label.bind("<Button-1>", self.status_bar_mgr.dismiss_message)
        
        # Legacy flags for compatibility
        self.error_showing = False
        self.is_flashing = False
        self.flash_after_id = None
        self.status_message_history = []
    
    def show_status_message(self, message, msg_type="info"):
        """Display a status message in the unified status bar"""
        self.status_bar_mgr.show_message(message, msg_type)
    
    def _update_initial_session(self):
        """Update session number after initial data load"""
        loaded_dog = sv.dog.get()
        if loaded_dog:
            db_ops = DatabaseOperations(self)
            status_filter = sv.session_status_filter.get()
            filtered_sessions = db_ops.get_all_sessions_for_dog(loaded_dog, status_filter)
            next_computed = len(filtered_sessions) + 1
            
            sv.session_number.set(str(next_computed))
            # print(f"DEBUG update_initial_session: set to computed {next_computed}")
            self.show_status_message(f"Ready - {loaded_dog} - Next session: #{next_computed}", "info")
            self.navigation.update_navigation_buttons()
    
    def _load_last_dog_for_air_session(self):
        """Load the last selected dog for air scenting session from database"""
        try:
            # Load default handler from config
            airscenting_config = self.config.get("airscenting", {})
            default_handler = airscenting_config.get("default_handler", "")
            if default_handler:
                sv.handler.set(default_handler)
            
            db_ops = DatabaseOperations(self)
            last_dog = db_ops.load_db_setting("last_dog_name", "")
            # print(f"DEBUG _load_last_dog_for_air_session: last_dog from db = '{last_dog}'")
            
            # Fall back to config if DB setting is empty (e.g. after DB rebuild)
            if not last_dog:
                last_dog = airscenting_config.get("last_dog", "")
            
            if last_dog:
                # Check if dog exists in the combobox values
                if hasattr(self, 'a_dog_combo'):
                    valid_dogs = self.a_dog_combo['values']
                    # print(f"DEBUG _load_last_dog_for_air_session: valid_dogs = {valid_dogs}")
                    if last_dog in valid_dogs:
                        sv.dog.set(last_dog)
                        # print(f"DEBUG _load_last_dog_for_air_session: set sv.dog to '{last_dog}'")
                        
                        # Update session number
                        status_filter = sv.session_status_filter.get()
                        filtered_sessions = db_ops.get_all_sessions_for_dog(
                            last_dog, status_filter, entry_type="Airscent"
                        )
                        next_computed = len(filtered_sessions) + 1
                        sv.session_number.set(str(next_computed))
                        
                        # Update status and navigation
                        self.show_status_message(f"Ready - {last_dog} - Next session: #{next_computed}", "info")
                        self.navigation.update_navigation_buttons()
                    else:
                        pass  # Dog not in valid dogs list
        except Exception as e:
            # print(f"Error loading last dog for air session: {e}")
            pass  # Non-critical error, dog can be selected manually
    
    # =========================================================================
    # BOOTSTRAP AND CONFIG
    # =========================================================================
    
    def load_bootstrap(self):
        """Load machine-specific paths from bootstrap file"""
        self.last_tab_index = 0  # Default to Setup tab
        
        if self.bootstrap_file.exists():
            try:
                with open(self.bootstrap_file, 'r') as f:
                    bootstrap = json.load(f)
                    
                    # Load last tab index
                    self.last_tab_index = bootstrap.get("last_tab", 0)
                    # print(f"DEBUG load_bootstrap: last_tab from file = {self.last_tab_index}")
                    
                    # Check for multi-user format
                    if "users" in bootstrap:
                        self.machine_current_user = bootstrap.get("current_user", "")
                        self.machine_user_list = list(bootstrap.get("users", {}).keys())
                        
                        if self.machine_current_user and self.machine_current_user in bootstrap.get("users", {}):
                            user_settings = bootstrap["users"][self.machine_current_user]
                            self.machine_db_path = user_settings.get("db_file_path", "")
                            self.machine_trail_maps_folder = user_settings.get("trail_maps_folder", "")
                            self.machine_backup_folder = user_settings.get("backup_folder", "")
                            self.machine_pdf_folder = user_settings.get("pdf_folder", "")
                            self.machine_excel_folder = user_settings.get("excel_folder", "")
                    else:
                        # Legacy format
                        default_user = getuser()
                        self.machine_current_user = default_user
                        self.machine_user_list = [default_user]
                        self.machine_db_path = bootstrap.get("db_file_path", "")
                        self.machine_trail_maps_folder = bootstrap.get("trail_maps_folder", "")
                        self.machine_backup_folder = bootstrap.get("backup_folder", "")
                        self.machine_pdf_folder = bootstrap.get("pdf_folder", "")
                        self.machine_excel_folder = bootstrap.get("excel_folder", "")
            except Exception as e:
                # print(f"Error loading bootstrap: {e}")
                pass  # Will use defaults
        
        if not self.machine_current_user:
            self.machine_current_user = getuser()
            self.machine_user_list = [self.machine_current_user]
    
    def save_bootstrap(self):
        """Save machine-specific paths to bootstrap file"""
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
                            "backup_folder": existing.get("backup_folder", ""),
                            "pdf_folder": existing.get("pdf_folder", ""),
                            "excel_folder": existing.get("excel_folder", "")
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
            "backup_folder": self.machine_backup_folder,
            "pdf_folder": self.machine_pdf_folder,
            "excel_folder": self.machine_excel_folder
        }
        
        self.machine_user_list = list(bootstrap["users"].keys())
        
        with open(self.bootstrap_file, 'w') as f:
            json.dump(bootstrap, f, indent=2)
    
    def load_config(self):
        """Load configuration from file"""
        # Try JSON folder first
        if self.machine_db_path:
            json_folder = Path(self.machine_db_path) / "JSON"
            json_config = json_folder / ".training_log_config.json"
            if json_config.exists():
                try:
                    with open(json_config, 'r') as f:
                        # print(f"Loaded config from JSON folder: {json_config}")
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
        # Ensure airscenting section exists
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
                            except Exception as e:
                                # print(f"Warning: Could not mirror config: {e}")
                                pass  # Non-critical, primary saved
                except Exception as e:
                    # print(f"Error saving config to JSON folder: {e}")
                    pass  # Non-critical, local config may work
        
        # # Also save to local config
        # try:
        #     with open(self.config_file, 'w') as f:
        #         json.dump(self.config, f, indent=2)
        # except Exception as e:
        #     # print(f"Error saving local config: {e}")
        #     pass  # Non-critical
    
    def get_json_config_path(self):
        """Get the path to config file in JSON folder"""
        if self.machine_db_path:
            json_folder = Path(self.machine_db_path) / "JSON"
            if json_folder.exists():
                return json_folder / ".training_log_config.json"
        return None
    
    # =========================================================================
    # MENU BAR
    # =========================================================================
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Manual (F1)", command=lambda: show_help_window(self.root))
        help_menu.add_command(label="About", command=self.show_about_dialog)
    
    def show_about_dialog(self):
        """Show the About dialog"""
        show_about(self.root, version=APP_VERSION,
                   app_title=APP_TITLE, github_url="https://" + GITHUB_URL)
    
    # =========================================================================
    # TAB HANDLING
    # =========================================================================
    
    def restore_last_tab(self):
        """Restore the last selected tab from bootstrap"""
        self._restoring_tab = True  # Prevent on_tab_changed from saving
        
        db_exists = False
        if self.machine_db_path:
            db_file = Path(self.machine_db_path) / "air_scenting.db"
            db_exists = db_file.exists()
        
        # print(f"DEBUG restore_last_tab: db_exists={db_exists}, last_tab_index={self.last_tab_index}")
        
        if not db_exists:
            self.notebook.select(self.setup_tab)
            self.previous_tab_index = 0
            self.last_tab_index = 0
            # print("No database found - starting on Setup tab")
            pass
            # Disable other tabs until database exists
            self.notebook.tab(1, state='disabled')
            self.notebook.tab(2, state='disabled')
            self._restoring_tab = False
            return
        
        # Database exists - enable all tabs
        self.notebook.tab(1, state='normal')
        self.notebook.tab(2, state='normal')
        
        last_tab = self.last_tab_index
        if last_tab < 0 or last_tab > 2:
            last_tab = 1  # Default to Air Scenting if invalid
        
        tabs = [self.setup_tab, self.airscent_tab, self.trailing_tab]
        self.notebook.select(tabs[last_tab])
        self.previous_tab_index = last_tab
        # print(f"Restored to last tab: {['Setup', 'Air Scenting', 'Trailing'][last_tab]}")
        
        # Clear flag after a short delay to allow the tab change event to complete
        self.root.after(100, self._clear_restoring_flag)
    
    def _clear_restoring_flag(self):
        """Clear the restoring flag after tab restore is complete"""
        self._restoring_tab = False
        # print(f"DEBUG: Tab restore complete, saving enabled")
    
    def on_tab_changed(self, event):
        """Handle tab change event"""
        current_tab_index = self.notebook.index(self.notebook.select())
        # print(f"DEBUG on_tab_changed: switching from {self.previous_tab_index} to {current_tab_index}, restoring={getattr(self, '_restoring_tab', False)}")
        
        # Skip saving if we're restoring the last tab on startup
        if getattr(self, '_restoring_tab', False):
            self.previous_tab_index = current_tab_index
            # print(f"DEBUG on_tab_changed: skipping save during restore")
            return
        
        # Check if trying to enter a session tab (index 1 or 2) after a restore
        if current_tab_index != 0 and sv.restart_required:
            messagebox.showwarning(
                "Restart Required",
                "A database restore has been performed.\n\n"
                "Please restart the program before entering session tabs\n"
                "to ensure data integrity."
            )
            self.notebook.select(self.setup_tab)
            self.previous_tab_index = 0
            return
        
        # Check if leaving Setup tab to a session tab
        if self.previous_tab_index == 0 and current_tab_index != 0:
            if not self.check_setup_requirements():
                self.notebook.select(self.setup_tab)
                self.previous_tab_index = 0
                return
            
            if not self.form_mgmt.check_unsaved_changes("switch tabs"):
                self.notebook.select(self.setup_tab)
                self.previous_tab_index = 0
                return
            
            # Enable session tabs now that setup is complete
            self.notebook.tab(1, state='normal')
            self.notebook.tab(2, state='normal')
        
        self.previous_tab_index = current_tab_index
        self.last_tab_index = current_tab_index
        self.save_bootstrap()
        # print(f"DEBUG on_tab_changed: saved last_tab_index={self.last_tab_index}")
    
    def check_setup_requirements(self):
        """Check if database and required folders are configured"""
        db_type = sv.db_type.get()
        
        if db_type == "sqlite":
            db_path = sv.db_path.get().strip()
            if not db_path:
                messagebox.showwarning("Setup Required",
                    "Please set the Database Folder before using the training session tabs.")
                return False
            
            db_file = Path(db_path) / "air_scenting.db"
            if not db_file.exists():
                messagebox.showwarning("Database Required",
                    "Please initialize data structures before using the training session tabs.")
                return False
        
        backup_folder = sv.backup_folder.get().strip()
        trail_maps_folder = sv.trail_maps_folder.get().strip()
        
        if not backup_folder or not trail_maps_folder:
            messagebox.showwarning("Setup Required",
                "Please set both the Backup Folder and Trail Maps Folder.")
            return False
        
        return True
    
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
        # print(f"DEBUG: Geometry saving now enabled")
    
    def _save_window_geometry(self):
        """Save current window geometry to config"""
        try:
            # Skip if maximized
            if os.name == 'nt':
                if self.root.state() == 'zoomed':
                    return
            else:
                try:
                    if self.root.attributes('-zoomed'):
                        return
                except:
                    pass
            
            geometry = self.root.geometry()
            self.config["window_geometry"] = geometry
            self.save_config()
            # print(f"DEBUG: Saved geometry '{geometry}'")
        except Exception as e:
            # print(f"Error saving window geometry: {e}")
            pass  # Non-critical
    
    # =========================================================================
    # WINDOW CLOSE
    # =========================================================================
    
    def on_closing(self):
        """Handle window close event"""
        # Check for unsaved session entry changes in airscenting
        if hasattr(self, 'form_mgmt') and hasattr(self.form_mgmt, 'check_entry_tab_changes'):
            if not self.form_mgmt.check_entry_tab_changes():
                return  # User cancelled
        
        # Check for unsaved setup/config changes in airscenting
        if hasattr(self, 'form_mgmt') and not self.form_mgmt.check_unsaved_changes("quit"):
            return
        
        # Check for unsaved changes in trailing
        if hasattr(self, 'trailing_entry') and hasattr(self.trailing_entry, 'has_unsaved_changes'):
            if self.trailing_entry.has_unsaved_changes():
                result = messagebox.askyesnocancel("Unsaved Changes",
                    "You have unsaved changes in the Trailing tab. Save before closing?",
                    icon='warning')
                if result is None:  # Cancel
                    return
                elif result:  # Yes - save
                    self.trailing_entry._save_session()
        
        # Perform exit backup sync to ensure all database changes are saved to JSON
        self._perform_exit_backup()
        
        # Save exit time to config for backup comparison on next startup
        self._save_exit_time()
        
        # Release session lock (deletes the lock file and cancels timers)
        if self.lock_manager:
            self.lock_manager.release()
        
        self.root.destroy()
    
    def _lock_force_exit(self):
        """Called by LockManager on inactivity timeout.

        Saves a snapshot of any unsaved form data, performs the exit backup,
        and releases the lock but does NOT prompt about unsaved form data.
        The LockManager handles root.destroy().
        """
        try:
            self._save_inactivity_snapshot()
        except Exception:
            pass
        try:
            self._perform_exit_backup()
        except Exception:
            pass
        try:
            self._save_exit_time()
        except Exception:
            pass
    
    def _save_exit_time(self):
        """Save the current time as exit time in config for backup comparison."""
        try:
            self.config["last_exit_time"] = datetime.now().isoformat()
            self.save_config()
        except:
            pass  # Don't block exit on config save errors
    
    def _perform_exit_backup(self):
        """Perform a full database backup on exit - dumps entire DB to a single JSON file."""
        try:
            # Get backup folders
            primary_folder = sv.db_path.get().strip()
            secondary_folder = sv.backup_folder.get().strip()
            
            if not primary_folder:
                return  # No primary folder configured
            
            primary_json = Path(primary_folder) / "JSON"
            if not primary_json.exists():
                return  # JSON folder doesn't exist
            
            # Show status message
            sv.show_status_message("Saving backup...", "info")
            self.root.update()
            
            # Export entire database to JSON
            backup_data = self._export_full_database()
            
            if not backup_data:
                return  # No data to backup
            
            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"full_backup_{timestamp}.json"
            
            # Write to primary JSON folder
            primary_backup_path = primary_json / backup_filename
            with open(primary_backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
            
            # Also write to secondary backup folder if configured
            if secondary_folder:
                secondary_json = Path(secondary_folder) / "JSON"
                if secondary_json.exists():
                    secondary_backup_path = secondary_json / backup_filename
                    try:
                        with open(secondary_backup_path, 'w', encoding='utf-8') as f:
                            json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
                    except:
                        pass  # Don't fail if secondary backup fails
            
            # Clean up old backups (keep last 10)
            self._cleanup_old_backups(primary_json)
            if secondary_folder:
                secondary_json = Path(secondary_folder) / "JSON"
                if secondary_json.exists():
                    self._cleanup_old_backups(secondary_json)
            
            # Also export sessions to Excel files
            self._export_sessions_to_excel(primary_folder, secondary_folder)
            
            # Sync image files between primary and secondary Images folders
            try:
                from backup_sync import sync_image_folders
                sync_image_folders(Path(primary_folder),
                                   Path(secondary_folder) if secondary_folder else None)
            except Exception:
                pass  # Don't block exit on image sync errors
            
        except Exception as e:
            # Don't block exit on backup errors
            pass
    
    def _export_sessions_to_excel(self, primary_folder, secondary_folder=None):
        """Export all sessions to Excel files in the dedicated Excel folder.
        
        If no Excel folder is configured in Setup, the export is skipped entirely.
        """
        try:
            excel_folder = sv.excel_folder.get().strip()
            
            # Only export when a dedicated Excel folder has been configured
            if not excel_folder:
                return
            
            from backup_management import export_all_sessions_to_excel
            
            db_type = sv.db_type.get()
            
            success, msg = export_all_sessions_to_excel(
                db_type, 
                excel_folder,
                None  # No secondary for dedicated Excel folder
            )
            # Silent - don't block exit
        except Exception as e:
            # Don't block exit on Excel export errors
            pass
    
    def _export_full_database(self):
        """Export entire database to a dictionary for JSON backup."""
        try:
            from sqlalchemy import text
            from database import get_connection
            
            backup_data = {
                "backup_version": "2.0",
                "backup_time": datetime.now().isoformat(),
                "airscenting_sessions": [],
                "trailing_sessions": [],
                "dogs": [],
                "locations": [],
                "terrain_types": [],
                "distraction_types": [],
                "config": self.config.copy() if hasattr(self, 'config') else {}
            }
            
            with get_connection() as conn:
                # Export airscenting sessions
                result = conn.execute(text("SELECT * FROM training_sessions"))
                columns = result.keys()
                for row in result:
                    session = dict(zip(columns, row))
                    backup_data["airscenting_sessions"].append(session)
                
                # Export trailing sessions
                result = conn.execute(text("SELECT * FROM t_training_sessions"))
                columns = result.keys()
                for row in result:
                    session = dict(zip(columns, row))
                    backup_data["trailing_sessions"].append(session)
                
                # Export dogs
                result = conn.execute(text("SELECT * FROM dogs"))
                columns = result.keys()
                for row in result:
                    backup_data["dogs"].append(dict(zip(columns, row)))
                
                # Export locations
                result = conn.execute(text("SELECT * FROM training_locations"))
                columns = result.keys()
                for row in result:
                    backup_data["locations"].append(dict(zip(columns, row)))
                
                # Export terrain types
                result = conn.execute(text("SELECT * FROM terrain_types"))
                columns = result.keys()
                for row in result:
                    backup_data["terrain_types"].append(dict(zip(columns, row)))
                
                # Export distraction types
                result = conn.execute(text("SELECT * FROM distraction_types"))
                columns = result.keys()
                for row in result:
                    backup_data["distraction_types"].append(dict(zip(columns, row)))
                
                # Export child tables (terrains, purposes, responses, distractions)
                # Table names must match schema.py exactly.
                try:
                    result = conn.execute(text("SELECT * FROM selected_terrains"))
                    columns = result.keys()
                    backup_data["selected_terrains"] = [dict(zip(columns, row)) for row in result]
                except:
                    pass
                
                try:
                    result = conn.execute(text("SELECT * FROM a_selected_purposes"))
                    columns = result.keys()
                    backup_data["a_selected_purposes"] = [dict(zip(columns, row)) for row in result]
                except:
                    pass
                
                try:
                    result = conn.execute(text("SELECT * FROM t_selected_terrains"))
                    columns = result.keys()
                    backup_data["t_selected_terrains"] = [dict(zip(columns, row)) for row in result]
                except:
                    pass
                
                try:
                    result = conn.execute(text("SELECT * FROM t_selected_purposes"))
                    columns = result.keys()
                    backup_data["t_selected_purposes"] = [dict(zip(columns, row)) for row in result]
                except:
                    pass
                
                try:
                    result = conn.execute(text("SELECT * FROM t_distractions"))
                    columns = result.keys()
                    backup_data["t_distractions"] = [dict(zip(columns, row)) for row in result]
                except:
                    pass
                
                try:
                    result = conn.execute(text("SELECT * FROM subject_responses"))
                    columns = result.keys()
                    backup_data["subject_responses"] = [dict(zip(columns, row)) for row in result]
                except:
                    pass
            
            return backup_data
            
        except Exception as e:
            return None
    
    def _cleanup_old_backups(self, json_folder, keep_count=10):
        """Remove old backup files, keeping only the most recent ones."""
        try:
            backup_files = list(json_folder.glob("full_backup_*.json"))
            if len(backup_files) <= keep_count:
                return
            
            # Sort by modification time (oldest first)
            backup_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Remove oldest files
            files_to_remove = backup_files[:-keep_count]
            for f in files_to_remove:
                try:
                    f.unlink()
                except:
                    pass
        except:
            pass
    
    # =========================================================================
    # INACTIVITY SNAPSHOT  (save unsaved form data on forced exit)
    # =========================================================================

    SNAPSHOT_FILENAME = "inactivity_snapshot.json"

    def _get_snapshot_path(self):
        """Return the Path to the inactivity snapshot file, or None."""
        primary_folder = sv.db_path.get().strip()
        if not primary_folder:
            return None
        json_folder = Path(primary_folder) / "JSON"
        if json_folder.exists():
            return json_folder / self.SNAPSHOT_FILENAME
        return None

    # -----------------------------------------------------------------
    # Collecting form data
    # -----------------------------------------------------------------

    def _collect_air_form_data(self):
        """Collect current Air Scenting form data into a dictionary.

        Returns None if no meaningful data has been entered.
        """
        import tkinter as tk

        # Quick check: is there any data worth saving?
        purpose = sv.session_purpose.get()
        field_support = sv.field_support.get()
        location = sv.location.get()
        search_area = sv.search_area_size.get()
        num_subjects = sv.num_subjects.get()
        handler_knowledge = sv.handler_knowledge.get()
        weather = sv.weather.get()
        temperature = sv.temperature.get()
        wind_direction = sv.wind_direction.get()
        wind_speed = sv.wind_speed.get()
        search_type = sv.search_type.get()
        drive_level = sv.drive_level.get()
        subjects_found = sv.subjects_found.get()
        a_percent_searched = sv.a_percent_searched.get()
        start_time = sv.start_time.get()
        finish_time = sv.finish_time.get()

        try:
            comments = self.a_comments_text.get("1.0", tk.END).strip()
        except (AttributeError, tk.TclError):
            comments = ""

        purposes = self.get_selected_purposes() if hasattr(self, 'get_selected_purposes') else []
        terrains = list(self.accumulated_terrains) if hasattr(self, 'accumulated_terrains') else []
        map_files = list(self.map_files_list) if hasattr(self, 'map_files_list') else []

        # Subject responses
        subject_responses = []
        try:
            for i in range(1, 11):
                item_id = f'subject_{i}'
                tags = self.a_subject_responses_tree.item(item_id, 'tags')
                if 'enabled' in tags:
                    values = self.a_subject_responses_tree.item(item_id, 'values')
                    tfr = values[1] if len(values) > 1 else ''
                    refind = values[2] if len(values) > 2 else ''
                    if tfr or refind:
                        subject_responses.append({
                            "subject_number": i,
                            "tfr": tfr,
                            "refind": refind
                        })
        except (AttributeError, tk.TclError):
            pass

        form_has_data = (
            purpose or field_support or location or search_area or
            num_subjects or handler_knowledge or weather or temperature or
            wind_direction or wind_speed or search_type or drive_level or
            subjects_found or a_percent_searched or start_time or finish_time or
            comments or purposes or terrains or map_files or subject_responses
        )

        if not form_has_data:
            return None

        try:
            date_val = self.a_date_picker.get_date().strftime("%Y-%m-%d")
        except Exception:
            date_val = sv.date.get()

        return {
            "date": date_val,
            "session_number": sv.session_number.get(),
            "handler": sv.handler.get(),
            "dog_name": sv.dog.get(),
            "session_purpose": purpose,
            "field_support": field_support,
            "location": location,
            "search_area_size": search_area,
            "num_subjects": num_subjects,
            "handler_knowledge": handler_knowledge,
            "weather": weather,
            "temperature": temperature,
            "wind_direction": wind_direction,
            "wind_speed": wind_speed,
            "search_type": search_type,
            "drive_level": drive_level,
            "subjects_found": subjects_found,
            "a_percent_searched": a_percent_searched,
            "start_time": start_time,
            "finish_time": finish_time,
            "comments": comments,
            "selected_purposes": purposes,
            "selected_terrains": terrains,
            "map_files": map_files,
            "subject_responses": subject_responses,
        }

    def _collect_trailing_form_data(self):
        """Collect current Trailing form data into a dictionary.

        Returns None if no meaningful data has been entered.
        """
        import tkinter as tk

        if not hasattr(self, 'trailing_entry'):
            return None

        te = self.trailing_entry

        # Check if trailing has unsaved changes compared to its snapshot
        try:
            if not te.has_unsaved_changes():
                return None
        except Exception:
            pass

        # Collect basic session data
        try:
            session_data = te.get_session_data()
        except Exception:
            return None

        # Collect child table data (terrains, purposes, distractions)
        try:
            terrains = list(te.terrain_listbox.get(0, tk.END))
        except (AttributeError, tk.TclError):
            terrains = []

        try:
            purposes = list(te.purpose_listbox.get(0, tk.END))
        except (AttributeError, tk.TclError):
            purposes = []

        distractions = []
        try:
            for item in te.distraction_tree.get_children():
                values = te.distraction_tree.item(item, 'values')
                if len(values) >= 2:
                    distractions.append({
                        "type": values[0],
                        "response": values[1]
                    })
        except (AttributeError, tk.TclError):
            pass

        # Quick check: is there any real data?
        has_data = False
        for key, val in session_data.items():
            if key in ('t_date', 't_session_number', 't_handler', 't_dog_name'):
                continue  # Skip identity fields
            if val:
                has_data = True
                break
        if not has_data and not terrains and not purposes and not distractions:
            return None

        session_data["t_selected_terrains"] = terrains
        session_data["t_selected_purposes"] = purposes
        session_data["t_distractions"] = distractions

        return session_data

    # -----------------------------------------------------------------
    # Save snapshot
    # -----------------------------------------------------------------

    def _save_inactivity_snapshot(self):
        """Save unsaved form data from both tabs to a JSON snapshot file.

        Called during forced exit (inactivity timeout) so that the data
        can be recovered on the next startup.
        """
        snapshot_path = self._get_snapshot_path()
        if not snapshot_path:
            return

        air_data = None
        trailing_data = None

        try:
            air_data = self._collect_air_form_data()
        except Exception:
            pass

        try:
            trailing_data = self._collect_trailing_form_data()
        except Exception:
            pass

        if not air_data and not trailing_data:
            return  # Nothing unsaved to snapshot

        snapshot = {
            "snapshot_version": "1.0",
            "snapshot_time": datetime.now().isoformat(),
            "reason": "inactivity_timeout",
        }
        if air_data:
            snapshot["air_scenting"] = air_data
        if trailing_data:
            snapshot["trailing"] = trailing_data

        try:
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2, default=str, ensure_ascii=False)
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Restore snapshot on next startup
    # -----------------------------------------------------------------

    def _check_and_restore_inactivity_snapshot(self):
        """Check for an inactivity snapshot and restore unsaved data.

        Called during startup after all widgets and initial data are loaded.
        If a snapshot is found the form data is restored, the user is warned,
        and the snapshot file is deleted.
        """
        snapshot_path = self._get_snapshot_path()
        if not snapshot_path or not snapshot_path.exists():
            return

        try:
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
        except Exception:
            # Corrupt or unreadable - remove it
            try:
                snapshot_path.unlink()
            except Exception:
                pass
            return

        air_data = snapshot.get("air_scenting")
        trailing_data = snapshot.get("trailing")
        snapshot_time = snapshot.get("snapshot_time", "unknown")

        restored_tabs = []

        # Restore Air Scenting data
        if air_data:
            try:
                self._restore_air_form_data(air_data)
                restored_tabs.append("Area Search")
            except Exception:
                pass

        # Restore Trailing data
        if trailing_data:
            try:
                self._restore_trailing_form_data(trailing_data)
                restored_tabs.append("Trailing")
            except Exception:
                pass

        # Delete the snapshot file after processing
        try:
            snapshot_path.unlink()
        except Exception:
            pass

        if not restored_tabs:
            return

        # Format a user-friendly timestamp
        try:
            dt = datetime.fromisoformat(snapshot_time)
            friendly_time = dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            friendly_time = snapshot_time

        tabs_text = " and ".join(restored_tabs)
        messagebox.showwarning(
            "Recovered Unsaved Data",
            f"The program was closed automatically due to inactivity on "
            f"{friendly_time}.\n\n"
            f"Unsaved session data from the {tabs_text} tab"
            f"{'s' if len(restored_tabs) > 1 else ''} has been restored "
            f"into the form.\n\n"
            f"Please review the data and save if correct."
        )

        self.show_status_message(
            f"Recovered unsaved data in {tabs_text} from {friendly_time}",
            "info"
        )

    def _restore_air_form_data(self, data):
        """Populate the Air Scenting form from a snapshot dictionary."""
        import tkinter as tk

        # Basic StringVar fields
        sv.date.set(data.get("date", ""))
        try:
            self.a_date_picker.set_date(
                datetime.strptime(data["date"], "%Y-%m-%d"))
        except Exception:
            pass

        sv.session_number.set(str(data.get("session_number", "")))
        sv.handler.set(data.get("handler", ""))
        sv.dog.set(data.get("dog_name", ""))
        sv.session_purpose.set(data.get("session_purpose", ""))
        sv.field_support.set(data.get("field_support", ""))
        sv.location.set(data.get("location", ""))
        sv.search_area_size.set(data.get("search_area_size", ""))
        sv.num_subjects.set(data.get("num_subjects", ""))
        sv.handler_knowledge.set(data.get("handler_knowledge", ""))
        sv.weather.set(data.get("weather", ""))
        sv.temperature.set(data.get("temperature", ""))
        sv.wind_direction.set(data.get("wind_direction", ""))
        sv.wind_speed.set(data.get("wind_speed", ""))
        sv.search_type.set(data.get("search_type", ""))
        sv.drive_level.set(data.get("drive_level", ""))
        sv.subjects_found.set(data.get("subjects_found", ""))
        sv.a_percent_searched.set(data.get("a_percent_searched", ""))
        sv.start_time.set(data.get("start_time", ""))
        sv.finish_time.set(data.get("finish_time", ""))

        # Time pickers
        from ui_form_management import TIME_PICKER_SET_BG, TIME_PICKER_NULL_BG
        for time_key, picker_attr, null_attr, color_setter in [
            ("start_time", "a_start_time_picker",
             "a_start_time_is_null", "_set_start_time_picker_color"),
            ("finish_time", "a_finish_time_picker",
             "a_finish_time_is_null", "_set_finish_time_picker_color"),
        ]:
            time_str = data.get(time_key, "")
            if time_str and hasattr(self, picker_attr):
                try:
                    picker = getattr(self, picker_attr)
                    if ':' in time_str:
                        h, m = time_str.split(':')
                        picker.set24Hrs(int(h))
                        picker.setMins(int(m))
                    elif len(time_str) == 4 and time_str.isdigit():
                        picker.set24Hrs(int(time_str[:2]))
                        picker.setMins(int(time_str[2:]))
                    setattr(self, null_attr, False)
                    getattr(self, color_setter)(TIME_PICKER_SET_BG)
                except Exception:
                    pass

        # Comments
        try:
            self.a_comments_text.delete("1.0", tk.END)
            comments = data.get("comments", "")
            if comments:
                self.a_comments_text.insert("1.0", comments)
        except (AttributeError, tk.TclError):
            pass

        # Terrains
        terrains = data.get("selected_terrains", [])
        if terrains:
            self.accumulated_terrains = list(terrains)
            if hasattr(self, 'a_accumulated_terrain_combo'):
                self.a_accumulated_terrain_combo['values'] = terrains
                sv.accumulated_terrain.set(terrains[0] if terrains else "")
            if hasattr(self, 'a_terrain_listbox'):
                self.a_terrain_listbox.delete(0, tk.END)
                for t in terrains:
                    self.a_terrain_listbox.insert(tk.END, t)

        # Purposes
        purposes = data.get("selected_purposes", [])
        if purposes and hasattr(self, 'a_purpose_listbox'):
            self.a_purpose_listbox.delete(0, tk.END)
            sv.a_purpose_list.clear()
            for p in purposes:
                self.a_purpose_listbox.insert(tk.END, p)
                sv.a_purpose_list.append(p)
            if hasattr(self, '_update_purpose_scrollbar'):
                self._update_purpose_scrollbar()

        # Map files
        map_files = data.get("map_files", [])
        if map_files:
            import os
            self.map_files_list = list(map_files)
            self.a_map_listbox.delete(0, tk.END)
            for filepath in map_files:
                self.a_map_listbox.insert(tk.END, os.path.basename(filepath))
            self.a_view_map_button.config(state=tk.NORMAL)
            self.a_delete_map_button.config(state=tk.NORMAL)

        # Subject responses
        subject_responses = data.get("subject_responses", [])
        num_subj = data.get("num_subjects", "")
        if num_subj:
            self.form_mgmt.update_subjects_found(preserve_value=True)
        for resp in subject_responses:
            sn = resp.get("subject_number", 0)
            item_id = f'subject_{sn}'
            try:
                if self.a_subject_responses_tree.exists(item_id):
                    self.a_subject_responses_tree.item(item_id, tags='enabled')
                    self.a_subject_responses_tree.item(item_id, values=(
                        f'Subject {sn}',
                        resp.get("tfr", ""),
                        resp.get("refind", "")
                    ))
            except (AttributeError, tk.TclError):
                pass

    def _restore_trailing_form_data(self, data):
        """Populate the Trailing form from a snapshot dictionary."""
        if not hasattr(self, 'trailing_entry'):
            return

        te = self.trailing_entry

        # Use the existing set_session_data for basic fields
        te.set_session_data(data)

        # Restore child lists
        terrains = data.get("t_selected_terrains", [])
        if terrains:
            te.set_selected_terrains(terrains)

        purposes = data.get("t_selected_purposes", [])
        if purposes:
            te.set_selected_purposes(purposes)

        distractions = data.get("t_distractions", [])
        if distractions:
            te.set_distractions(distractions)

    # =========================================================================
    # AIRSCENTING METHODS (delegated from air_ui.py)
    # =========================================================================
    
    def save_session(self):
        """Save the current airscenting session - delegated to misc2_ops"""
        return self.misc2_ops.save_session()
    
    # =========================================================================
    # DATA REFRESH METHODS (consolidated - updates both tabs)
    # =========================================================================
    
    def load_locations_from_database(self):
        """Load locations and update both tabs - delegate to Setup tab manager"""
        self.setup_tab_mgr.load_locations_from_database()
        # Also refresh Entry tab combos
        self.refresh_location_list()
    
    def load_dogs_from_database(self):
        """Load dogs and update both tabs - delegate to Setup tab manager"""
        self.setup_tab_mgr.load_dogs_from_database()
        # Also refresh Entry tab combos
        self.refresh_dog_list()
    
    def load_terrain_from_database(self):
        """Load terrain types and update both tabs - delegate to Setup tab manager"""
        self.setup_tab_mgr.load_terrain_from_database()
        # Also refresh Entry tab combos
        self.refresh_terrain_list()
    
    def load_distraction_from_database(self):
        """Load distraction types - delegate to Setup tab manager"""
        self.setup_tab_mgr.load_distraction_from_database()
    
    def refresh_location_list(self):
        """Refresh location combobox in Air Scenting tab AND Trailing tab"""
        from ui_database import get_db_manager
        
        try:
            self.misc_data_ops.ensure_db_ready()
            db_mgr = get_db_manager(sv.db_type.get())
            locations = db_mgr.load_locations()
            sorted_locations = sorted(locations) if locations else []
            
            # Update Air Scenting tab
            if hasattr(self, 'a_location_combo'):
                self.a_location_combo['values'] = sorted_locations
            
            # Update Trailing tab
            if hasattr(self, 'trailing_entry'):
                self.trailing_entry.update_location_list(sorted_locations)
                
        except Exception as e:
            # print(f"Error refreshing location list: {e}")
            pass  # Non-critical
    
    def refresh_dog_list(self):
        """Refresh dog combobox in Air Scenting tab AND Trailing tab"""
        from ui_database import get_db_manager
        
        try:
            # Save current selection before refreshing
            current_dog = sv.dog.get()
            # print(f"DEBUG refresh_dog_list: current dog before refresh = '{current_dog}'")
            
            self.misc_data_ops.ensure_db_ready()
            db_mgr = get_db_manager(sv.db_type.get())
            dogs = db_mgr.load_dogs()
            # print(f"DEBUG refresh_dog_list: loaded dogs = {dogs}")
            
            # Update Air Scenting tab
            if hasattr(self, 'a_dog_combo'):
                self.a_dog_combo['values'] = dogs if dogs else []
            
            # Update Trailing tab
            if hasattr(self, 'trailing_entry'):
                self.trailing_entry.update_dog_list(dogs if dogs else [])
            
            # Restore selection if it was valid
            if current_dog and dogs and current_dog in dogs:
                sv.dog.set(current_dog)
                # print(f"DEBUG refresh_dog_list: restored dog = '{current_dog}'")
                
        except Exception as e:
            # print(f"Error refreshing dog list: {e}")
            pass  # Non-critical
    
    def refresh_terrain_list(self):
        """Refresh terrain combobox in Air Scenting tab AND Trailing tab"""
        from ui_database import get_db_manager
        
        try:
            self.misc_data_ops.ensure_db_ready()
            db_mgr = get_db_manager(sv.db_type.get())
            terrain_types = db_mgr.load_terrain_types()
            
            # Fallback to defaults if empty
            if not terrain_types:
                terrain_types = self.config.get("terrain_types", [])
            if not terrain_types:
                from ui_utils import get_default_terrain_types
                terrain_types = get_default_terrain_types()
            
            # Update Air Scenting tab
            if hasattr(self, 'a_terrain_combo'):
                self.a_terrain_combo['values'] = terrain_types
            
            # Update Trailing tab
            if hasattr(self, 'trailing_entry'):
                self.trailing_entry.update_terrain_types(terrain_types)
                
        except Exception as e:
            # print(f"Error refreshing terrain list: {e}")
            pass  # Non-critical
    
    def refresh_distraction_list(self):
        """Refresh distraction types in Trailing tab"""
        from ui_database import get_db_manager
        
        try:
            self.misc_data_ops.ensure_db_ready()
            db_mgr = get_db_manager(sv.db_type.get())
            distraction_types = db_mgr.load_distraction_types()
            
            # Fallback to defaults if empty
            if not distraction_types:
                distraction_types = self.config.get("distraction_types", [])
            if not distraction_types:
                from ui_utils import get_default_distraction_types
                distraction_types = get_default_distraction_types()
            
            # Update Trailing tab
            if hasattr(self, 'trailing_entry'):
                self.trailing_entry.update_distraction_types(distraction_types)
                
        except Exception as e:
            # print(f"Error refreshing distraction list: {e}")
            pass  # Non-critical
    
    # =========================================================================
    # DELEGATE METHODS (for setup_tab and other modules)
    # =========================================================================
    
    def update_location_button_states(self, *args):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.update_location_button_states(*args)
    
    def on_location_select(self, event):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.on_location_select(event)
    
    def add_location(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.add_location()
    
    def remove_location(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.remove_location()
    
    def update_dog_button_states(self, *args):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.update_dog_button_states(*args)
    
    def on_dog_select(self, event):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.on_dog_select(event)
    
    def add_dog(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.add_dog()
    
    def remove_dog(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.remove_dog()
    
    def update_terrain_button_states(self, *args):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.update_terrain_button_states(*args)
    
    def on_terrain_select(self, event):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.on_terrain_select(event)
    
    def add_terrain_type(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.add_terrain_type()
    
    def remove_terrain_type(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.remove_terrain_type()
    
    def move_terrain_up(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.move_terrain_up()
    
    def move_terrain_down(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.move_terrain_down()
    
    def restore_default_terrain_types(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.restore_default_terrain_types()
    
    def update_distraction_type_button_states(self, *args):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.update_distraction_type_button_states(*args)
    
    def on_distraction_type_select(self, event):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.on_distraction_type_select(event)
    
    def add_distraction_type(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.add_distraction_type()
    
    def remove_distraction_type(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.remove_distraction_type()
    
    def move_distraction_up(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.move_distraction_up()
    
    def move_distraction_down(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.move_distraction_down()
    
    def restore_default_distraction_types(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.restore_default_distraction_types()
    
    def save_configuration_settings(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.save_configuration_settings()
    
    def update_create_db_button_state(self, *args):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.update_create_db_button_state()
    
    # =========================================================================
    # RUN
    # =========================================================================
    
    def run(self):
        """Start the application main loop"""
        self.root.mainloop()


# =========================================================================
# MAIN ENTRY POINT
# =========================================================================

if __name__ == "__main__":
    app = TrainingLoggerUI()
    app.run()
