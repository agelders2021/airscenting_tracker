"""
SPDX-License-Identifier: GPL-3.0-or-later

Copyright (C) 2026 Al Gelders

This file is part of the airscenting an trailing logging programs

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
UI Module for Trailing Logger
Main application window and controller
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import json
import os
from pathlib import Path
from datetime import datetime
from getpass import getuser
from t_config import APP_TITLE, CONFIG_FILE, BOOTSTRAP_FILE, T_APP_TITLE, T_GITHUB_URL

# =============================================================================
# CRITICAL: Configure database path BEFORE importing modules that use database.py
# The database.py module creates its engine at import time, so we must update
# the config BEFORE any imports that trigger database.py to load.
# =============================================================================
def _configure_database_path_from_bootstrap():
    """Load bootstrap and configure database path before database module is imported.
    
    This must be called BEFORE importing t_ui_database or any module that imports database.py,
    because database.py creates its engine at import time with the URL from config.
    """
    import config as original_config
    
    # Load bootstrap to get machine-specific paths
    if BOOTSTRAP_FILE.exists():
        try:
            with open(BOOTSTRAP_FILE, 'r') as f:
                bootstrap = json.load(f)
                
                # Check for new multi-user format
                if "users" in bootstrap:
                    current_user = bootstrap.get("current_user", "")
                    if current_user and current_user in bootstrap.get("users", {}):
                        user_settings = bootstrap["users"][current_user]
                        machine_db_path = user_settings.get("db_file_path", "")
                    else:
                        machine_db_path = ""
                else:
                    # Legacy format
                    machine_db_path = bootstrap.get("db_file_path", "")
                
                # Update config with the correct database path
                if machine_db_path:
                    db_file = Path(machine_db_path) / "air_scenting.db"
                    original_config.DB_CONFIG["sqlite"]["url"] = f"sqlite:///{db_file}"
                    return machine_db_path
        except Exception as e:
            print(f"Warning: Could not load bootstrap for database path: {e}")
    
    return ""

# Configure database path BEFORE importing database-dependent modules
_early_db_path = _configure_database_path_from_bootstrap()

# Now it's safe to import modules that use database.py
from splash_screen import SplashScreen
from about_dialog import show_about
from tips import ToolTip
from ui_utils import get_username, get_default_terrain_types, get_default_distraction_types
from working_dialog import WorkingDialog
from setup_tab import SetupTab
from ui_file_operations import FileOperations
from ui_misc_data_ops import MiscDataOperations
import sv
from t_ui_database import DatabaseOperations, get_db_manager


class TrailingUI:
    """Main UI class for Trailing Logger"""
    
    def __init__(self):
        """Initialize the UI"""
        # Load configuration
        self.config_file = CONFIG_FILE
        self.bootstrap_file = BOOTSTRAP_FILE
        
        # Initialize machine-specific paths
        # Use early-loaded path if available (from module-level initialization)
        self.machine_db_path = _early_db_path
        self.machine_trail_maps_folder = ""
        self.machine_backup_folder = ""
        self.machine_current_user = ""
        self.machine_user_list = []
        
        # Load full bootstrap (for trail_maps_folder, backup_folder, etc.)
        self.load_bootstrap()
        
        # If db_path changed in load_bootstrap, update the database config
        # (This handles the case where bootstrap was modified after module load)
        import config as original_config
        if self.machine_db_path and self.machine_db_path != _early_db_path:
            db_file = Path(self.machine_db_path) / "air_scenting.db"
            original_config.DB_CONFIG["sqlite"]["url"] = f"sqlite:///{db_file}"
            # Dispose old engine so new connection uses updated path
            from database import engine
            engine.dispose()
        
        # Load config
        self.config = self.load_config()
        
        # Create main window
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
        
        self.root.withdraw()
        
        # Show splash screen
        self.splash = SplashScreen(self.root, version="1.0.6-alpha", 
                                   app_title=T_APP_TITLE, github_url=T_GITHUB_URL)
        
        # Set window properties
        self.root.title(APP_TITLE)
        
        window_width = 1200
        window_height = 900
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x_position = (screen_width - window_width) // 2
        y_position = 0
        
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.root.minsize(window_width, 800)
        self.root.minsize(window_height,950)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bind to tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.previous_tab_index = 0  # Track which tab we're coming from
        
        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.entry_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.setup_tab, text="Setup")
        self.notebook.add(self.entry_tab, text="Trailing Session Entry")
        
        # Initialize helper classes needed by SetupTab
        self.file_ops = FileOperations(self)
        self.misc_data_ops = MiscDataOperations(self)
        
        # Initialize airscenting-style attributes that SetupTab needs
        self.selected_sessions = []
        self.selected_sessions_index = -1
        self.a_dog_combo = None
        self.a_location_combo = None
        self.a_terrain_combo = None
        
        # Create stub navigation object
        self.navigation = type('Navigation', (), {
            'update_navigation_buttons': lambda self: None
        })()
        
        # Create stub form_mgmt object
        self.form_mgmt = type('FormMgmt', (), {
            'update_subjects_found': lambda self: None,
            'take_form_snapshot': lambda self: None
        })()
        
        # Setup the tabs using shared SetupTab
        self.setup_tab_manager = SetupTab(self)
        self.setup_tab_manager.setup_setup_tab()
        self.setup_entry_tab()
        
        # Status bar frame at bottom
        status_bar_frame = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create status bar widgets with proper Unicode arrows
        self.status_left_arrow = tk.Button(status_bar_frame, text="\u25C0", 
                                           width=2, state="disabled")
        self.status_left_arrow.pack(side=tk.LEFT, padx=(2, 0))
        
        self.status_right_arrow = tk.Button(status_bar_frame, text="\u25B6", 
                                            width=2, state="disabled")
        self.status_right_arrow.pack(side=tk.LEFT, padx=(2, 0))
        
        self.status_cancel_button = tk.Button(status_bar_frame, text="Cancel Msg", 
                                              width=10, 
                                              relief=tk.RAISED,
                                              cursor="hand2")
        self.status_cancel_button.pack(side=tk.LEFT, padx=(5, 2))
        
        self.status_label = tk.Label(status_bar_frame, textvariable=sv.t_status,
                                     anchor=tk.W, padx=5, pady=2)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Initialize StatusBarManager for 3-queue priority system
        from status_bar import StatusBarManager
        self.status_bar_mgr = StatusBarManager(
            root=self.root,
            status_var=sv.t_status,
            status_label=self.status_label,
            left_arrow=self.status_left_arrow,
            right_arrow=self.status_right_arrow,
            cancel_button=self.status_cancel_button
        )
        
        # Bind click on label to dismiss
        self.status_label.bind("<Button-1>", self.status_bar_mgr.dismiss_message)
        
        # Legacy flags kept for compatibility
        self.error_showing = False
        self.is_flashing = False
        self.flash_after_id = None
        self.status_message_history = []
        
        # Show main window
        self.root.deiconify()
        self.root.update()
        
        # Load initial data
        self.root.after(500, self.load_initial_data)
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_bootstrap(self):
        """Load machine-specific paths from bootstrap file.
        
        Bootstrap JSON structure supports multiple users:
        {
            "current_user": "username",
            "users": {
                "username": {
                    "db_file_path": "...",
                    "trail_maps_folder": "...",
                    "backup_folder": "..."
                }
            }
        }
        
        Legacy format (single user) is auto-migrated:
        {
            "db_file_path": "...",
            "trail_maps_folder": "...",
            "backup_folder": "..."
        }
        """
        if self.bootstrap_file.exists():
            try:
                with open(self.bootstrap_file, 'r') as f:
                    bootstrap = json.load(f)
                    
                    # Check for new multi-user format
                    if "users" in bootstrap:
                        # New format
                        self.machine_current_user = bootstrap.get("current_user", "")
                        self.machine_user_list = list(bootstrap.get("users", {}).keys())
                        
                        # Load current user's settings
                        if self.machine_current_user and self.machine_current_user in bootstrap.get("users", {}):
                            user_settings = bootstrap["users"][self.machine_current_user]
                            self.machine_db_path = user_settings.get("db_file_path", "")
                            self.machine_trail_maps_folder = user_settings.get("trail_maps_folder", "")
                            self.machine_backup_folder = user_settings.get("backup_folder", "")
                    else:
                        # Legacy format - migrate to new format
                        # Use system username as default user
                        default_user = getuser()
                        self.machine_current_user = default_user
                        self.machine_user_list = [default_user]
                        self.machine_db_path = bootstrap.get("db_file_path", "")
                        self.machine_trail_maps_folder = bootstrap.get("trail_maps_folder", "")
                        self.machine_backup_folder = bootstrap.get("backup_folder", "")
                        
                        # Save in new format (migration happens automatically on next save)
            except:
                pass
        
        # If no bootstrap file exists or no current user set, default to system username
        if not self.machine_current_user:
            self.machine_current_user = getuser()
            self.machine_user_list = [self.machine_current_user]
    
    def save_bootstrap(self):
        """Save machine-specific paths to bootstrap file.
        
        Uses multi-user structure:
        {
            "current_user": "username",
            "users": {
                "username": {
                    "db_file_path": "...",
                    "trail_maps_folder": "...",
                    "backup_folder": "..."
                }
            }
        }
        """
        # Load existing bootstrap data or create new structure
        bootstrap = {
            "current_user": "",
            "users": {}
        }
        
        if self.bootstrap_file.exists():
            try:
                with open(self.bootstrap_file, 'r') as f:
                    existing = json.load(f)
                    
                    # Handle legacy format migration
                    if "users" in existing:
                        bootstrap = existing
                    else:
                        # Migrate legacy format
                        default_user = getuser()
                        bootstrap["current_user"] = default_user
                        bootstrap["users"][default_user] = {
                            "db_file_path": existing.get("db_file_path", ""),
                            "trail_maps_folder": existing.get("trail_maps_folder", ""),
                            "backup_folder": existing.get("backup_folder", "")
                        }
            except:
                pass
        
        # Ensure current user is set
        if not self.machine_current_user:
            self.machine_current_user = getuser()
        
        # Update current user
        bootstrap["current_user"] = self.machine_current_user
        
        # Update/add user's settings
        bootstrap["users"][self.machine_current_user] = {
            "db_file_path": self.machine_db_path,
            "trail_maps_folder": self.machine_trail_maps_folder,
            "backup_folder": self.machine_backup_folder
        }
        
        # Update user list
        self.machine_user_list = list(bootstrap["users"].keys())
        
        # Save to bootstrap file
        with open(self.bootstrap_file, 'w') as f:
            json.dump(bootstrap, f, indent=2)
    
    # ===== STUB METHODS FOR SETUPTAB COMPATIBILITY =====
    # These methods delegate to SetupTab for trailing's Setup tab
    
    def set_date(self, date_str):
        """Set date - stub for SetupTab compatibility"""
        sv.t_date.set(date_str)
    
    def load_dogs_from_database(self):
        """Load dogs from database - delegate to SetupTab"""
        if hasattr(self, 'setup_tab_manager'):
            self.setup_tab_manager.refresh_dog_list()
    
    def load_locations_from_database(self):
        """Load locations from database - delegate to SetupTab"""
        if hasattr(self, 'setup_tab_manager'):
            self.setup_tab_manager.load_locations_from_database()
    
    def load_terrain_from_database(self):
        """Load terrain from database - delegate to SetupTab"""
        if hasattr(self, 'setup_tab_manager'):
            self.setup_tab_manager.load_terrain_from_database()
    
    def load_distraction_from_database(self):
        """Load distraction types from database - delegate to SetupTab"""
        if hasattr(self, 'setup_tab_manager'):
            self.setup_tab_manager.load_distraction_from_database()
    
    def refresh_dog_list(self):
        """Refresh dog combobox - delegate to SetupTab"""
        if hasattr(self, 'setup_tab_manager'):
            self.setup_tab_manager.refresh_dog_list()
    
    def refresh_location_list(self):
        """Refresh location combobox - delegate to SetupTab"""
        if hasattr(self, 'setup_tab_manager'):
            self.setup_tab_manager.load_locations_from_database()
    
    def refresh_terrain_list(self):
        """Refresh terrain combobox - delegate to SetupTab"""
        if hasattr(self, 'setup_tab_manager'):
            self.setup_tab_manager.load_terrain_from_database()
    
    # ===== END STUB METHODS =====
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_dialog)
    
    def show_about_dialog(self):
        """Show the About dialog"""
        show_about(self.root, version="1.0.6-alpha", 
                   app_title=T_APP_TITLE, github_url="https://" + T_GITHUB_URL)
    
    def get_json_config_path(self):
        """Get the path to config file in JSON folder"""
        if self.machine_db_path:
            json_folder = Path(self.machine_db_path) / "JSON"
            if json_folder.exists():
                return json_folder / ".training_log_config.json"
        return None
    
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "terrain_types": get_default_terrain_types(),
            "distraction_types": get_default_distraction_types(),
            "training_locations": [],
            "dog_names": [],
            "db_type": "sqlite",
            "airscenting": {
                "default_handler": "",
                "last_handler": ""
            },
            "trailing": {
                "default_handler": "",
                "last_dog": ""
            }
        }
        
        json_config_path = self.get_json_config_path()
        
        if json_config_path and json_config_path.exists():
            try:
                with open(json_config_path, 'r') as f:
                    saved = json.load(f)
                    
                    # Migrate old format if needed
                    if "airscenting" not in saved:
                        saved["airscenting"] = {
                            "default_handler": saved.get("handler_name", ""),
                            "last_handler": saved.get("last_handler_name", "")
                        }
                        saved.pop("handler_name", None)
                        saved.pop("last_handler_name", None)
                    
                    if "trailing" not in saved:
                        saved["trailing"] = {
                            "default_handler": "",
                            "last_dog": ""
                        }
                    
                    default_config.update(saved)
            except:
                pass
        
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        from ui_utils import get_secondary_json_folder
        
        json_config_path = self.get_json_config_path()
        if not json_config_path:
            print("save_config: No JSON config path available")
            return
        
        json_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"Config saved to primary: {json_config_path}")
        
        # Mirror to secondary
        secondary_folder = get_secondary_json_folder(create_if_missing=True)
        if secondary_folder:
            secondary_config_path = secondary_folder / ".training_log_config.json"
            try:
                with open(secondary_config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
                print(f"Config mirrored to secondary: {secondary_config_path}")
            except Exception as e:
                print(f"Warning: Failed to mirror config: {e}")
        else:
            print(f"save_config: No secondary folder (backup_folder={sv.backup_folder.get()})")
    
    def setup_entry_tab(self):
        """Setup the Trailing Entry tab"""
        from ui_trailing import TrailingEntryTab
        
        # Create callbacks for the entry tab
        callbacks = {
            'on_save': self.on_session_save,
            'get_next_session_number': self.get_next_session_number,
            'on_load_prior_session': self.on_load_prior_session,
            'on_navigate_previous': self.on_navigate_previous,
            'on_navigate_next': self.on_navigate_next,
            'on_export_pdf': self.on_export_pdf,
            'on_resume_session': self.on_resume_session,
            'on_hide_session': self.on_hide_session,
        }
        
        # Create the entry tab
        self.trailing_entry = TrailingEntryTab(self.entry_tab, self, callbacks)
    
    def on_session_save(self, session_data):
        """Handle session save from entry tab"""
        db_ops = DatabaseOperations(self)
        
        # Check if this is an update or new session
        is_update = hasattr(self.trailing_entry, 'editing_session') and self.trailing_entry.editing_session
        
        success, session_id, message = db_ops.save_session(session_data, is_update)
        
        if success:
            # Save related data if we have a session_id
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
                self.save_session_to_json(session_data, terrains, purposes, distractions)
            
            # Clear form and set up for next session
            # After both new saves and updates, prepare for a new session
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
            # Print error to console AND status bar
            print(f"ERROR saving session: {message}")
            self.show_status_message(f"Error: {message}", "error")
            return False
    
    def save_session_to_json(self, session_data, terrains, purposes, distractions):
        """Save trailing session to JSON backup file.
        
        Uses consistent naming: t_{user}_{dog}_{session_number}.json
        Updates database with checksum and file timestamps.
        """
        import re
        from ui_utils import save_json_mirrored
        
        try:
            # Get user_name for filename and data
            user_name = get_username()
            
            # Build the backup data
            backup_data = {
                **session_data,
                "selected_terrains": terrains,
                "selected_purposes": purposes,
                "distractions": distractions,
                "user_name": user_name,
                "update_time": datetime.now().isoformat()
            }
            
            # Get session info for filename (session_number from DB, not calculated)
            dog_name = session_data.get('t_dog_name', 'unknown')
            session_num = session_data.get('t_session_number', '0')
            
            # Sanitize names for filename
            safe_user_name = re.sub(r'[^\w\-]', '_', user_name) if user_name else 'unknown'
            safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
            
            # Consistent naming convention: t_{user}_{dog}_{session}.json
            filename = f"t_{safe_user_name}_{safe_dog_name}_{session_num}.json"
            
            # Save to both primary and secondary (returns checksum and timestamps)
            primary, secondary, checksum, primary_ts, secondary_ts = save_json_mirrored(filename, backup_data)
            
            if primary:
                print(f"Trailing session saved to JSON: {primary}")
            if secondary:
                print(f"Trailing session mirrored to: {secondary}")
            
            # Update database with checksum and timestamps
            if checksum:
                try:
                    self._update_trailing_backup_info(session_num, dog_name, checksum, primary_ts, secondary_ts)
                except Exception as e:
                    print(f"Warning: Could not update backup info in DB: {e}")
                
        except Exception as e:
            error_msg = f"Backup failed: {str(e)}"
            print(f"Warning: Failed to save trailing session to JSON: {e}")
            self.show_status_message(error_msg, "error")
    
    def _update_trailing_backup_info(self, session_number, dog_name, checksum, primary_ts, secondary_ts):
        """Update checksum and timestamps in database for a trailing session."""
        try:
            from sqlalchemy import text
            from database import get_connection
            
            with get_connection() as conn:
                conn.execute(text("""
                    UPDATE t_training_sessions SET
                        checksum = :checksum,
                        primary_timestamp = :primary_ts,
                        secondary_timestamp = :secondary_ts
                    WHERE t_session_number = :session_number AND t_dog_name = :dog_name
                """), {
                    'checksum': checksum,
                    'primary_ts': primary_ts,
                    'secondary_ts': secondary_ts,
                    'session_number': session_number,
                    'dog_name': dog_name
                })
                conn.commit()
                print(f"Updated trailing backup info: checksum={checksum[:16]}...")
        except Exception as e:
            print(f"Error updating trailing session backup info: {e}")
    
    def get_next_session_number(self, dog_name):
        """Get next session number for a dog"""
        db_ops = DatabaseOperations(self)
        return db_ops.get_next_session_number(dog_name)
    
    def on_load_prior_session(self):
        """Open dialog to view/edit/delete prior sessions"""
        from tkinter import Toplevel, Listbox, Scrollbar
        
        # Block if sync is in progress
        if sv.sync_in_progress:
            messagebox.showinfo(
                "Sync In Progress",
                "Please wait - background sync is in progress.\n\n"
                "Edit/Hide operations are temporarily disabled to ensure data integrity.\n"
                "This should only take a few seconds."
            )
            return
        
        dog_name = sv.t_dog.get()
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first.")
            return
        
        # Get sessions for this dog based on filter
        db_ops = DatabaseOperations(self)
        status_filter = sv.t_session_status_filter.get()
        sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter=status_filter.capitalize())
        
        if not sessions:
            messagebox.showinfo("No Sessions", f"No sessions found for {dog_name}")
            return
        
        # Create selection dialog
        dialog = Toplevel(self.root)
        dialog.title("Select Sessions to View/Edit/Hide")
        dialog.geometry("650x450")
        dialog.transient(self.root)
        
        # Instructions
        instructions = tk.Label(
            dialog,
            text="Select sessions to navigate:\n"
                 "\u2022 Click to select one session\n"
                 "\u2022 Ctrl+Click to select multiple sessions\n"
                 "\u2022 Shift+Click to select a range\n"
                 "Use Previous/Next buttons to navigate through selected sessions",
            justify="left",
            padx=10,
            pady=10
        )
        instructions.pack()
        
        # Listbox with scrollbar
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        session_listbox = Listbox(list_frame, selectmode="extended", yscrollcommand=scrollbar.set, 
                                  font=("Courier", 10), width=70)
        session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=session_listbox.yview)
        
        # Store session data for lookup
        session_data_list = []
        
        def populate_listbox(sessions_to_show):
            """Populate the listbox with session data"""
            session_listbox.delete(0, tk.END)
            session_data_list.clear()
            
            for session in sessions_to_show:
                session_num = session.get('t_session_number', '?')
                date = session.get('t_date', '')
                handler = session.get('t_handler', '') or ''
                location = session.get('t_location', '') or ''
                status = session.get('status', 'active')
                status_marker = " [HIDDEN]" if status == 'deleted' else ""
                
                # Format: Session #  |  Date  |  Handler  |  Location
                display_text = f"#{session_num:3d}  |  {str(date):10s}  |  {handler:15s}  |  {location:20s}{status_marker}"
                session_listbox.insert(tk.END, display_text)
                session_data_list.append(session)
        
        # Initial population
        populate_listbox(sessions)
        
        # Store the list for navigation
        self.trailing_entry.dog_sessions_list = sessions
        
        def refresh_sessions():
            """Refresh the session list based on current filter"""
            status_filter = sv.t_session_status_filter.get()
            new_sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter=status_filter.capitalize())
            populate_listbox(new_sessions)
            self.trailing_entry.dog_sessions_list = new_sessions
            
            # Update button text based on filter
            if status_filter == 'deleted':
                delete_button.config(text="Restore Selected", bg="#28a745")
            else:
                delete_button.config(text="Hide Selected", bg="#DC143C")
        
        # Filter radiobuttons
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
            """Load selected sessions for viewing/editing"""
            selected_indices = session_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            # Get selected sessions
            selected_sessions = [session_data_list[i] for i in selected_indices]
            self.trailing_entry.dog_sessions_list = selected_sessions
            self.trailing_entry.current_session_index = 0
            
            # Load the first selected session
            self._load_session_into_form(selected_sessions[0])
            self._update_navigation_buttons()
            
            dialog.destroy()
            
            self.show_status_message(f"Viewing {len(selected_sessions)} selected session(s)", "info")
        
        def delete_restore_selected():
            """Handle delete/restore based on current filter"""
            selected_indices = session_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            selected_sessions = [session_data_list[i] for i in selected_indices]
            selected_nums = [s.get('t_session_number') for s in selected_sessions]
            status_filter = sv.t_session_status_filter.get()
            
            if status_filter == 'deleted':
                # Restore sessions
                result = messagebox.askyesno(
                    "Confirm Restore",
                    f"Restore {len(selected_nums)} session(s) to active?\n\n"
                    f"Sessions: {', '.join(map(str, selected_nums))}",
                    icon='question'
                )
                
                if result:
                    for session_num in selected_nums:
                        db_ops.update_session_status(session_num, dog_name, 'active')
                    self.show_status_message(f"Restored {len(selected_nums)} session(s)", "info")
                    dialog.destroy()
            else:
                # Hide sessions
                result = messagebox.askyesno(
                    "Confirm Hide",
                    f"Mark {len(selected_nums)} session(s) as hidden?\n\n"
                    f"Sessions: {', '.join(map(str, selected_nums))}\n\n"
                    "This can be undone by restoring the sessions.",
                    icon='warning'
                )
                
                if result:
                    for session_num in selected_nums:
                        db_ops.update_session_status(session_num, dog_name, 'deleted')
                    self.show_status_message(f"Hidden {len(selected_nums)} session(s)", "info")
                    dialog.destroy()
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="View Selected", command=view_selected, 
                  bg="#4169E1", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        # Context-aware button text based on filter
        status_filter = sv.t_session_status_filter.get()
        if status_filter == 'deleted':
            button_text = "Restore Selected"
            button_color = "#28a745"
        else:
            button_text = "Hide Selected"
            button_color = "#DC143C"
        
        delete_button = tk.Button(btn_frame, text=button_text, command=delete_restore_selected,
                                   bg=button_color, fg="white", width=15)
        delete_button.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        # Double-click to view
        session_listbox.bind('<Double-Button-1>', lambda e: view_selected())
    
    def _load_session_into_form(self, session_data):
        """Load session data into the form for editing"""
        self.trailing_entry.set_session_data(session_data)
        self.trailing_entry.editing_session = True
        self.trailing_entry.editing_row = session_data.get('id')
        self.trailing_entry.update_save_button_text()  # Change button to "Update Session"
        
        # Load related data (terrains, purposes, distractions)
        session_id = session_data.get('id')
        if session_id:
            db_ops = DatabaseOperations(self)
            
            # Load terrains
            terrains = db_ops.load_selected_terrains(session_id)
            self.trailing_entry.set_selected_terrains(terrains)
            
            # Load purposes
            purposes = db_ops.load_selected_purposes(session_id)
            self.trailing_entry.set_selected_purposes(purposes)
            
            # Load distractions
            distractions = db_ops.load_distractions(session_id)
            self.trailing_entry.set_distractions(distractions)
        
        # Enable/disable Hide and Restore buttons based on session status
        session_status = session_data.get('status', 'active')
        if session_status == 'deleted':
            # Hidden session - disable Hide, enable Restore
            if hasattr(self.trailing_entry, 'hide_btn'):
                self.trailing_entry.hide_btn.config(state=tk.DISABLED)
            if hasattr(self.trailing_entry, 'resume_btn'):
                self.trailing_entry.resume_btn.config(state=tk.NORMAL)
        else:
            # Active session - enable Hide, disable Restore
            if hasattr(self.trailing_entry, 'hide_btn'):
                self.trailing_entry.hide_btn.config(state=tk.NORMAL)
            if hasattr(self.trailing_entry, 'resume_btn'):
                self.trailing_entry.resume_btn.config(state=tk.DISABLED)
        
        self.show_status_message(f"Loaded session {session_data.get('t_session_number')} for editing", "info")
    
    def _update_navigation_buttons(self):
        """Update prev/next button states"""
        if not self.trailing_entry.dog_sessions_list:
            self.trailing_entry.prev_session_btn.config(state=tk.DISABLED)
            self.trailing_entry.next_session_btn.config(state=tk.DISABLED)
            return
        
        idx = self.trailing_entry.current_session_index
        max_idx = len(self.trailing_entry.dog_sessions_list) - 1
        
        self.trailing_entry.prev_session_btn.config(state=tk.NORMAL if idx > 0 else tk.DISABLED)
        self.trailing_entry.next_session_btn.config(state=tk.NORMAL if idx < max_idx else tk.DISABLED)
    
    def on_navigate_previous(self):
        """Navigate to previous session"""
        if not self.trailing_entry.dog_sessions_list:
            return
        
        idx = self.trailing_entry.current_session_index
        if idx > 0:
            self.trailing_entry.current_session_index = idx - 1
            session = self.trailing_entry.dog_sessions_list[idx - 1]
            self._load_session_into_form(session)
            self._update_navigation_buttons()
    
    def on_navigate_next(self):
        """Navigate to next session"""
        if not self.trailing_entry.dog_sessions_list:
            return
        
        idx = self.trailing_entry.current_session_index
        max_idx = len(self.trailing_entry.dog_sessions_list) - 1
        if idx < max_idx:
            self.trailing_entry.current_session_index = idx + 1
            session = self.trailing_entry.dog_sessions_list[idx + 1]
            self._load_session_into_form(session)
            self._update_navigation_buttons()
    
    def on_resume_session(self):
        """Restore (undelete) the currently displayed session"""
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
        
        # Confirm action
        result = messagebox.askyesno(
            "Restore Session",
            f"Mark session {session_num} for {dog_name} as active?",
            icon='question'
        )
        
        if result:
            db_ops = DatabaseOperations(self)
            success = db_ops.update_session_status(session_num, dog_name, 'active')
            
            if success:
                self.show_status_message(f"Session {session_num} restored to active", "info")
                
                # Update the session in the dog_sessions_list if present
                for session in self.trailing_entry.dog_sessions_list:
                    if session.get('t_session_number') == session_num:
                        session['status'] = 'active'
                        break
                
                # Reload session to update display (including frame title)
                idx = self.trailing_entry.current_session_index
                if 0 <= idx < len(self.trailing_entry.dog_sessions_list):
                    self._load_session_into_form(self.trailing_entry.dog_sessions_list[idx])
            else:
                messagebox.showerror("Error", "Failed to restore session")
    
    def on_hide_session(self):
        """Mark the currently displayed session as hidden (deleted)"""
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
        
        # Confirm action
        result = messagebox.askyesno(
            "Hide Session",
            f"Mark session {session_num} for {dog_name} as hidden?\n\n"
            "This can be undone with the Restore button.",
            icon='warning'
        )
        
        if result:
            db_ops = DatabaseOperations(self)
            success = db_ops.update_session_status(session_num, dog_name, 'deleted')
            
            if success:
                self.show_status_message(f"Session {session_num} marked as hidden", "info")
                
                # Update the session in the dog_sessions_list if present
                for session in self.trailing_entry.dog_sessions_list:
                    if session.get('t_session_number') == session_num:
                        session['status'] = 'deleted'
                        break
                
                # Reload session to update display (including frame title)
                idx = self.trailing_entry.current_session_index
                if 0 <= idx < len(self.trailing_entry.dog_sessions_list):
                    self._load_session_into_form(self.trailing_entry.dog_sessions_list[idx])
            else:
                messagebox.showerror("Error", "Failed to hide session")

    def on_export_pdf(self):
        """Export sessions to PDF using list-based selection like View/Edit/Hide"""
        from tkinter import Toplevel, Listbox, Scrollbar
        
        dog_name = sv.t_dog.get()
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first.")
            return
        
        # Create dialog
        dialog = Toplevel(self.root)
        dialog.title("Export Sessions to PDF")
        dialog.geometry("650x500")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Dog display at top
        header_frame = tk.Frame(dialog, padx=10, pady=10)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="Dog:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(header_frame, text=dog_name, font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(5, 0))
        
        # Instructions
        instructions = tk.Label(
            dialog,
            text="Select sessions to export:\n"
                 "â€¢ Click to select one session\n"
                 "â€¢ Ctrl+Click to select multiple sessions\n"
                 "â€¢ Shift+Click to select a range",
            justify="left",
            padx=10,
            pady=5
        )
        instructions.pack()
        
        # Status filter radiobuttons
        filter_frame = tk.Frame(dialog)
        filter_frame.pack(pady=(5, 5))
        
        tk.Label(filter_frame, text="Show Sessions:").pack(side=tk.LEFT, padx=(0, 10))
        export_status_var = tk.StringVar(value="active")
        
        # Listbox with scrollbar
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        session_listbox = Listbox(list_frame, selectmode="extended", yscrollcommand=scrollbar.set,
                                  font=("Courier", 10), width=70)
        session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=session_listbox.yview)
        
        # Store session data for lookup
        session_data_list = []
        
        def populate_listbox():
            """Populate the listbox with session data"""
            session_listbox.delete(0, tk.END)
            session_data_list.clear()
            
            db_ops = DatabaseOperations(self)
            status_filter = export_status_var.get()
            sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter=status_filter.capitalize() if status_filter != "both" else "All")
            
            for session in sessions:
                session_num = session.get('t_session_number', '?')
                date = session.get('t_date', '')
                handler = session.get('t_handler', '') or ''
                location = session.get('t_location', '') or ''
                status = session.get('status', 'active')
                status_marker = " [HIDDEN]" if status == 'deleted' else ""
                
                # Format: Session #  |  Date  |  Handler  |  Location
                display_text = f"#{session_num:3d}  |  {str(date):10s}  |  {handler:15s}  |  {location:20s}{status_marker}"
                session_listbox.insert(tk.END, display_text)
                session_data_list.append(session)
            
            # Select all by default
            if session_data_list:
                session_listbox.select_set(0, tk.END)
        
        def on_filter_changed():
            """Handle filter radiobutton change"""
            populate_listbox()
        
        # Add radiobuttons
        tk.Radiobutton(filter_frame, text="Active", variable=export_status_var,
                      value="active", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(filter_frame, text="Hidden", variable=export_status_var,
                      value="deleted", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(filter_frame, text="Both", variable=export_status_var,
                      value="both", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
        
        # Initial population
        populate_listbox()
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def do_export():
            selected_indices = session_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session to export")
                return
            
            # Get selected sessions
            selected_sessions = [session_data_list[i] for i in selected_indices]
            selected_nums = [s.get('t_session_number') for s in selected_sessions]
            
            # Get file save location
            default_filename = f"Trailing_Log_{dog_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
            filepath = filedialog.asksaveasfilename(
                title="Save PDF As",
                defaultextension=".pdf",
                initialfile=default_filename,
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            
            if not filepath:
                return
            
            dialog.destroy()
            
            # Export with selected sessions
            self._export_trailing_sessions_by_selection(filepath, dog_name, selected_nums)
        
        tk.Button(button_frame, text="Export", command=do_export, bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
    
    def _export_trailing_sessions_to_pdf(self, filepath, dog_name, range_type, start_value, end_value, sort_order, status_filter):
        """Export multiple trailing sessions to PDF file - comprehensive export like airscenting"""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        
        try:
            # Fetch sessions
            db_ops = DatabaseOperations(self)
            sessions = db_ops.get_trailing_sessions_for_export(
                dog_name, range_type, start_value, end_value, sort_order, status_filter
            )
            
            if not sessions:
                messagebox.showinfo("No Sessions", "No sessions found matching the specified criteria")
                return
            
            # Get trail maps folder for images
            trail_maps_folder = sv.trail_maps_folder.get().strip()
            
            doc = SimpleDocTemplate(filepath, pagesize=letter, 
                                    rightMargin=0.5*inch, leftMargin=0.5*inch,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            styles = getSampleStyleSheet()
            
            # Custom styles matching airscenting
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#2E4057'),
                spaceAfter=20,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#4CAF50'),
                spaceAfter=6,
                spaceBefore=6
            )
            
            label_style = ParagraphStyle(
                'Label',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                spaceAfter=2
            )
            
            value_style = ParagraphStyle(
                'Value',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=8
            )
            
            elements = []
            
            # Title
            elements.append(Paragraph(f"Trailing Training Log for {dog_name}", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            for i, session_data in enumerate(sessions):
                if i > 0:
                    # Page break after every 2 sessions
                    if i % 2 == 0:
                        elements.append(PageBreak())
                    else:
                        # Separator line
                        elements.append(Spacer(1, 0.15*inch))
                        elements.append(Table([['']], colWidths=[7*inch], 
                                         style=[('LINEABOVE', (0,0), (-1,-1), 1, colors.grey)]))
                        elements.append(Spacer(1, 0.15*inch))
                
                # Session header
                session_num = session_data.get('t_session_number', '?')
                date_str = str(session_data.get('t_date', '')) if session_data.get('t_date') else ''
                elements.append(Paragraph(f"<b>Session #{session_num}</b> - {date_str}", heading_style))
                elements.append(Spacer(1, 0.1*inch))
                
                # Helper function to add fields to table
                def add_field(label, value):
                    if value and str(value).strip():
                        return [Paragraph(f"<b>{label}:</b>", label_style), 
                                Paragraph(str(value), value_style)]
                    return None
                
                # Session Information
                elements.append(Paragraph("<b>Session Information</b>", heading_style))
                session_info_data = []
                
                fields = [
                    ('Handler', session_data.get('t_handler')),
                    ('Field Support', session_data.get('t_field_support')),
                    ('Location', session_data.get('t_location')),
                    ('Start Time', session_data.get('t_start_time')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        session_info_data.append(row)
                
                # Add session purposes (comma-separated if multiple)
                purposes = session_data.get('purposes', [])
                if purposes:
                    purposes_str = ', '.join(purposes) if isinstance(purposes, list) else str(purposes)
                    row = add_field('Session Purposes', purposes_str)
                    if row:
                        session_info_data.append(row)
                
                if session_info_data:
                    table = Table(session_info_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                elements.append(Spacer(1, 0.1*inch))
                
                # Trail Details (renamed from Trail Information)
                elements.append(Paragraph("<b>Trail Details</b>", heading_style))
                trail_info_data = []
                
                fields = [
                    ('Trail Age', session_data.get('t_trail_age')),
                    ('Trail Length', session_data.get('t_trail_length')),
                    ('Difficulty', session_data.get('t_difficulty')),
                    ('Trail Layer', session_data.get('t_trail_layer')),
                    ('Cross-Track Layer', session_data.get('t_cross_track_layer')),
                    ('Cross-Track Age', session_data.get('t_cross_track_age')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        trail_info_data.append(row)
                
                # Add terrain types
                terrains = session_data.get('terrains', [])
                if terrains:
                    terrain_text = ", ".join(terrains)
                    row = add_field('Terrain Types', terrain_text)
                    if row:
                        trail_info_data.append(row)
                
                if trail_info_data:
                    table = Table(trail_info_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                elements.append(Spacer(1, 0.1*inch))
                
                # Weather Conditions - Laying
                laying_weather = []
                fields = [
                    ('Weather', session_data.get('t_weather_laying')),
                    ('Temperature', session_data.get('t_temperature_laying')),
                    ('Wind Speed', session_data.get('t_wind_speed_laying')),
                    ('Wind Direction', session_data.get('t_wind_direction_laying')),
                    ('Humidity', session_data.get('t_humidity_laying')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        laying_weather.append(row)
                
                if laying_weather:
                    elements.append(Paragraph("<b>Weather Conditions (Laying)</b>", heading_style))
                    table = Table(laying_weather, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 0.1*inch))
                
                # Weather Conditions - Running
                running_weather = []
                fields = [
                    ('Weather', session_data.get('t_weather_running')),
                    ('Temperature', session_data.get('t_temperature_running')),
                    ('Wind Speed', session_data.get('t_wind_speed_running')),
                    ('Wind Direction', session_data.get('t_wind_direction_running')),
                    ('Humidity', session_data.get('t_humidity_running')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        running_weather.append(row)
                
                if running_weather:
                    elements.append(Paragraph("<b>Weather Conditions (Running)</b>", heading_style))
                    table = Table(running_weather, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 0.1*inch))
                
                # Dog Behavior
                behavior_data = []
                fields = [
                    ('Start Behavior', session_data.get('t_start_behavior')),
                    ('Consistency', session_data.get('t_consistency')),
                    ('Head Position', session_data.get('t_head_position')),
                    ('Pace', session_data.get('t_pace')),
                    ('Indication', session_data.get('t_indication')),
                    ('Time to Complete', session_data.get('t_time_to_complete')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        behavior_data.append(row)
                
                # Parse distractions for inclusion in Dog Behavior
                distractions = session_data.get('distractions', [])
                distraction_table_data = []
                if distractions:
                    for d in distractions:
                        if d:
                            distraction_type = ''
                            response = ''
                            
                            # Handle different data formats
                            if isinstance(d, dict):
                                # Already a dictionary
                                distraction_type = d.get('type', '') or d.get('distraction', '')
                                response = d.get('response', '') or d.get('dog_response', '')
                            elif isinstance(d, str):
                                # Try JSON first
                                try:
                                    import json
                                    parsed = json.loads(d)
                                    if isinstance(parsed, dict):
                                        distraction_type = parsed.get('type', '') or parsed.get('distraction', '')
                                        response = parsed.get('response', '') or parsed.get('dog_response', '')
                                except (json.JSONDecodeError, ValueError):
                                    # Try ast.literal_eval for Python dict strings
                                    try:
                                        import ast
                                        parsed = ast.literal_eval(d)
                                        if isinstance(parsed, dict):
                                            distraction_type = parsed.get('type', '') or parsed.get('distraction', '')
                                            response = parsed.get('response', '') or parsed.get('dog_response', '')
                                    except (ValueError, SyntaxError):
                                        # Just use the string as-is
                                        distraction_type = str(d)
                            
                            if distraction_type or response:
                                distraction_table_data.append([str(distraction_type), str(response)])
                
                # Check if we have behavior data or distractions
                has_behavior = bool(behavior_data)
                has_distractions = bool(distraction_table_data)
                
                if has_behavior or has_distractions:
                    elements.append(Paragraph("<b>Dog Behavior</b>", heading_style))
                    
                    # Add behavior fields
                    if has_behavior:
                        table = Table(behavior_data, colWidths=[1.5*inch, 5.5*inch])
                        table.setStyle(TableStyle([
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('TOPPADDING', (0,0), (-1,-1), 2),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                        ]))
                        elements.append(table)
                    
                    # Add distractions as a row with table - only if there are distractions
                    if has_distractions:
                        # Create distractions table with headers
                        distraction_header = [['Distraction', 'Response']]
                        full_distraction_table = distraction_header + distraction_table_data
                        
                        # Distractions data table
                        d_table = Table(full_distraction_table, colWidths=[2*inch, 3*inch])
                        d_table.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0E0E0')),
                            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0,0), (-1,-1), 9),
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                            ('TOPPADDING', (0,0), (-1,-1), 4),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                            ('LEFTPADDING', (0,0), (-1,-1), 4),
                        ]))
                        
                        # Add as a row matching behavior_data format: "Distractions:" | table
                        distraction_row = [
                            Paragraph(f"<b>Distractions:</b>", label_style),
                            d_table
                        ]
                        distraction_wrapper = Table([distraction_row], colWidths=[1.5*inch, 5.5*inch])
                        distraction_wrapper.setStyle(TableStyle([
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('TOPPADDING', (0,0), (-1,-1), 2),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                        ]))
                        elements.append(distraction_wrapper)
                    
                    elements.append(Spacer(1, 0.1*inch))
                
                # Impression/Comments
                impression = session_data.get('t_impression', '')
                if impression and str(impression).strip():
                    elements.append(Paragraph("<b>Overall Impression</b>", heading_style))
                    impression_text = str(impression).replace('\n', '<br/>')
                    elements.append(Paragraph(impression_text, value_style))
                    elements.append(Spacer(1, 0.1*inch))
                
                # Maps and Images
                map_files_str = session_data.get('t_map_files', '')
                if map_files_str and trail_maps_folder:
                    # Parse image files - stored as JSON list
                    image_files = []
                    if map_files_str:
                        try:
                            import json
                            # Try to parse as JSON first (new format)
                            parsed = json.loads(map_files_str)
                            if isinstance(parsed, list):
                                image_files = [f.strip() for f in parsed if f and f.strip()]
                            else:
                                image_files = [str(parsed).strip()] if parsed else []
                        except (json.JSONDecodeError, TypeError):
                            # Fallback to comma/semicolon separated (legacy format)
                            image_files = [f.strip() for f in map_files_str.replace(';', ',').split(',') if f.strip()]
                    
                    if image_files:
                        elements.append(Paragraph("<b>Maps and Images</b>", heading_style))
                        
                        for image_file in image_files:
                            if image_file:
                                # Handle both full paths and just filenames
                                if os.path.isabs(image_file):
                                    image_path = image_file
                                else:
                                    image_path = os.path.join(trail_maps_folder, image_file)
                                
                                if os.path.exists(image_path):
                                    try:
                                        file_ext = os.path.splitext(image_file)[1].lower()
                                        
                                        if file_ext in ['.jpg', '.jpeg', '.png']:
                                            img = Image(image_path, width=6.5*inch, height=6.5*inch, kind='proportional')
                                            elements.append(img)
                                            elements.append(Spacer(1, 0.05*inch))
                                            # Show just filename in caption
                                            display_name = os.path.basename(image_file)
                                            caption = Paragraph(f"<i>{display_name}</i>", label_style)
                                            elements.append(caption)
                                            elements.append(Spacer(1, 0.1*inch))
                                        elif file_ext == '.pdf':
                                            display_name = os.path.basename(image_file)
                                            note_text = f"<i>{display_name}</i><br/><font color='blue'>PDF file (not embedded)</font>"
                                            elements.append(Paragraph(note_text, value_style))
                                            elements.append(Spacer(1, 0.1*inch))
                                    except Exception as e:
                                        display_name = os.path.basename(image_file)
                                        error_text = f"<i>{display_name}</i><br/><font color='red'>Error loading image: {str(e)}</font>"
                                        elements.append(Paragraph(error_text, value_style))
                                        elements.append(Spacer(1, 0.1*inch))
                                else:
                                    display_name = os.path.basename(image_file)
                                    error_text = f"<i>{display_name}</i><br/><font color='red'>File not found: {image_path}</font>"
                                    elements.append(Paragraph(error_text, value_style))
                                    elements.append(Spacer(1, 0.1*inch))
            
            doc.build(elements)
            
            # Send success message to status bar instead of popup
            self.show_status_message(f"Exported {len(sessions)} session(s) to: {filepath}", "info")
            
            # Ask to open
            if messagebox.askyesno("Open File?", "Would you like to open the exported PDF?"):
                import subprocess
                import platform
                if platform.system() == 'Windows':
                    os.startfile(filepath)
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', filepath])
                else:
                    subprocess.run(['xdg-open', filepath])
                    
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export PDF:\n{e}")
            print(f"PDF export error: {e}")
            import traceback
            traceback.print_exc()
    
    def _export_trailing_sessions_by_selection(self, filepath, dog_name, session_numbers):
        """Export selected trailing sessions to PDF file
        
        Args:
            filepath: Path to save PDF
            dog_name: Name of the dog
            session_numbers: List of session numbers to export
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        
        try:
            # Fetch sessions by specific numbers
            db_ops = DatabaseOperations(self)
            sessions = db_ops.get_trailing_sessions_by_numbers(dog_name, session_numbers)
            
            if not sessions:
                messagebox.showinfo("No Sessions", "No sessions found matching the selection")
                return
            
            # Get trail maps folder for images
            trail_maps_folder = sv.trail_maps_folder.get().strip()
            
            doc = SimpleDocTemplate(filepath, pagesize=letter, 
                                    rightMargin=0.5*inch, leftMargin=0.5*inch,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            styles = getSampleStyleSheet()
            
            # Custom styles matching airscenting
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#2E4057'),
                spaceAfter=20,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#4CAF50'),
                spaceAfter=6,
                spaceBefore=6
            )
            
            label_style = ParagraphStyle(
                'Label',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                spaceAfter=2
            )
            
            value_style = ParagraphStyle(
                'Value',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=8
            )
            
            elements = []
            
            # Title
            elements.append(Paragraph(f"Trailing Training Log for {dog_name}", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            for i, session_data in enumerate(sessions):
                if i > 0:
                    # Page break after every 2 sessions
                    if i % 2 == 0:
                        elements.append(PageBreak())
                    else:
                        # Separator line
                        elements.append(Spacer(1, 0.15*inch))
                        elements.append(Table([['']], colWidths=[7*inch], 
                                         style=[('LINEABOVE', (0,0), (-1,-1), 1, colors.grey)]))
                        elements.append(Spacer(1, 0.15*inch))
                
                # Session header
                session_num = session_data.get('t_session_number', '?')
                date_str = str(session_data.get('t_date', '')) if session_data.get('t_date') else ''
                elements.append(Paragraph(f"<b>Session #{session_num}</b> - {date_str}", heading_style))
                elements.append(Spacer(1, 0.1*inch))
                
                # Helper function to add fields to table
                def add_field(label, value):
                    if value and str(value).strip():
                        return [Paragraph(f"<b>{label}:</b>", label_style), 
                                Paragraph(str(value), value_style)]
                    return None
                
                # Session Information
                elements.append(Paragraph("<b>Session Information</b>", heading_style))
                session_info_data = []
                
                fields = [
                    ('Handler', session_data.get('t_handler')),
                    ('Field Support', session_data.get('t_field_support')),
                    ('Location', session_data.get('t_location')),
                    ('Start Time', session_data.get('t_start_time')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        session_info_data.append(row)
                
                # Add session purposes (comma-separated if multiple)
                purposes = session_data.get('purposes', [])
                if purposes:
                    purposes_str = ', '.join(purposes) if isinstance(purposes, list) else str(purposes)
                    row = add_field('Session Purposes', purposes_str)
                    if row:
                        session_info_data.append(row)
                
                if session_info_data:
                    table = Table(session_info_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                elements.append(Spacer(1, 0.1*inch))
                
                # Trail Details
                elements.append(Paragraph("<b>Trail Details</b>", heading_style))
                trail_info_data = []
                
                fields = [
                    ('Trail Age', session_data.get('t_trail_age')),
                    ('Trail Length', session_data.get('t_trail_length')),
                    ('Difficulty', session_data.get('t_difficulty')),
                    ('Trail Layer', session_data.get('t_trail_layer')),
                    ('Cross-Track Layer', session_data.get('t_cross_track_layer')),
                    ('Cross-Track Age', session_data.get('t_cross_track_age')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        trail_info_data.append(row)
                
                # Add terrains (comma-separated if multiple)
                terrains = session_data.get('terrains', [])
                if terrains:
                    terrains_str = ', '.join(terrains) if isinstance(terrains, list) else str(terrains)
                    row = add_field('Terrain Types', terrains_str)
                    if row:
                        trail_info_data.append(row)
                
                if trail_info_data:
                    table = Table(trail_info_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                elements.append(Spacer(1, 0.1*inch))
                
                # Weather Information
                elements.append(Paragraph("<b>Weather Information</b>", heading_style))
                weather_data = []
                
                # Weather when laying trail
                fields = [
                    ('Weather (Laying)', session_data.get('t_weather_laying')),
                    ('Temperature (Laying)', session_data.get('t_temp_laying')),
                    ('Wind Speed (Laying)', session_data.get('t_wind_laying')),
                    ('Wind Direction (Laying)', session_data.get('t_wind_direction_laying')),
                    ('Humidity (Laying)', session_data.get('t_humidity_laying')),
                    ('Weather (Running)', session_data.get('t_weather_running')),
                    ('Temperature (Running)', session_data.get('t_temp_running')),
                    ('Wind Speed (Running)', session_data.get('t_wind_running')),
                    ('Wind Direction (Running)', session_data.get('t_wind_direction_running')),
                    ('Humidity (Running)', session_data.get('t_humidity_running')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        weather_data.append(row)
                
                if weather_data:
                    table = Table(weather_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                elements.append(Spacer(1, 0.1*inch))
                
                # Behavior and Distractions
                behavior_fields = [
                    ('Start Behavior', session_data.get('t_start_behavior')),
                    ('Consistency', session_data.get('t_consistency')),
                    ('Head Position', session_data.get('t_head_pos')),
                    ('Pace', session_data.get('t_pace')),
                    ('Indication', session_data.get('t_indication')),
                    ('Time Taken', session_data.get('t_time')),
                    ('Success', session_data.get('t_success')),
                ]
                behavior_data = []
                has_behavior = False
                for label, value in behavior_fields:
                    row = add_field(label, value)
                    if row:
                        behavior_data.append(row)
                        has_behavior = True
                
                # Get distractions
                distractions = session_data.get('distractions', [])
                distraction_table_data = []
                has_distractions = False
                for d in distractions:
                    d_type = d.get('t_distraction_type', '')
                    d_response = d.get('t_response', '')
                    if d_type or d_response:
                        distraction_table_data.append([d_type, d_response])
                        has_distractions = True
                
                if has_behavior or has_distractions:
                    elements.append(Paragraph("<b>Behavior & Distractions</b>", heading_style))
                    
                    if has_behavior:
                        table = Table(behavior_data, colWidths=[1.5*inch, 5.5*inch])
                        table.setStyle(TableStyle([
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('TOPPADDING', (0,0), (-1,-1), 2),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                        ]))
                        elements.append(table)
                    
                    if has_distractions:
                        distraction_header = [['Distraction', 'Response']]
                        full_distraction_table = distraction_header + distraction_table_data
                        
                        d_table = Table(full_distraction_table, colWidths=[2*inch, 3*inch])
                        d_table.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0E0E0')),
                            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0,0), (-1,-1), 9),
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                            ('TOPPADDING', (0,0), (-1,-1), 4),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                            ('LEFTPADDING', (0,0), (-1,-1), 4),
                        ]))
                        
                        distraction_row = [
                            Paragraph(f"<b>Distractions:</b>", label_style),
                            d_table
                        ]
                        distraction_wrapper = Table([distraction_row], colWidths=[1.5*inch, 5.5*inch])
                        distraction_wrapper.setStyle(TableStyle([
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('TOPPADDING', (0,0), (-1,-1), 2),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                        ]))
                        elements.append(distraction_wrapper)
                    
                    elements.append(Spacer(1, 0.1*inch))
                
                # Impression/Comments
                impression = session_data.get('t_impression', '')
                if impression and str(impression).strip():
                    elements.append(Paragraph("<b>Overall Impression</b>", heading_style))
                    impression_text = str(impression).replace('\n', '<br/>')
                    elements.append(Paragraph(impression_text, value_style))
                    elements.append(Spacer(1, 0.1*inch))
                
                # Maps and Images
                map_files_str = session_data.get('t_map_files', '')
                if map_files_str and trail_maps_folder:
                    image_files = []
                    if map_files_str:
                        try:
                            import json
                            parsed = json.loads(map_files_str)
                            if isinstance(parsed, list):
                                image_files = [f.strip() for f in parsed if f and f.strip()]
                            else:
                                image_files = [str(parsed).strip()] if parsed else []
                        except (json.JSONDecodeError, TypeError):
                            image_files = [f.strip() for f in map_files_str.replace(';', ',').split(',') if f.strip()]
                    
                    if image_files:
                        elements.append(Paragraph("<b>Maps and Images</b>", heading_style))
                        
                        for image_file in image_files:
                            if image_file:
                                if os.path.isabs(image_file):
                                    image_path = image_file
                                else:
                                    image_path = os.path.join(trail_maps_folder, image_file)
                                
                                if os.path.exists(image_path):
                                    try:
                                        file_ext = os.path.splitext(image_file)[1].lower()
                                        
                                        if file_ext in ['.jpg', '.jpeg', '.png']:
                                            img = Image(image_path, width=6.5*inch, height=6.5*inch, kind='proportional')
                                            elements.append(img)
                                            elements.append(Spacer(1, 0.05*inch))
                                            display_name = os.path.basename(image_file)
                                            caption = Paragraph(f"<i>{display_name}</i>", label_style)
                                            elements.append(caption)
                                            elements.append(Spacer(1, 0.1*inch))
                                        elif file_ext == '.pdf':
                                            display_name = os.path.basename(image_file)
                                            note_text = f"<i>{display_name}</i><br/><font color='blue'>PDF file (not embedded)</font>"
                                            elements.append(Paragraph(note_text, value_style))
                                            elements.append(Spacer(1, 0.1*inch))
                                    except Exception as e:
                                        display_name = os.path.basename(image_file)
                                        error_text = f"<i>{display_name}</i><br/><font color='red'>Error loading image: {str(e)}</font>"
                                        elements.append(Paragraph(error_text, value_style))
                                        elements.append(Spacer(1, 0.1*inch))
                                else:
                                    display_name = os.path.basename(image_file)
                                    error_text = f"<i>{display_name}</i><br/><font color='red'>File not found: {image_path}</font>"
                                    elements.append(Paragraph(error_text, value_style))
                                    elements.append(Spacer(1, 0.1*inch))
            
            doc.build(elements)
            
            # Send success message to status bar
            self.show_status_message(f"Exported {len(sessions)} session(s) to: {filepath}", "info")
            
            # Ask to open
            if messagebox.askyesno("Open File?", "Would you like to open the exported PDF?"):
                import subprocess
                import platform
                if platform.system() == 'Windows':
                    os.startfile(filepath)
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', filepath])
                else:
                    subprocess.run(['xdg-open', filepath])
                    
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export PDF:\n{e}")
            print(f"PDF export error: {e}")
            import traceback
            traceback.print_exc()
    
    def load_initial_data(self):
        """Load initial data after UI is ready"""
        # Print startup info
        print("=" * 60)
        print("Trailing Logger Starting")
        print("=" * 60)
        print(f"Database path: {self.machine_db_path or 'Not configured'}")
        print(f"Trail maps folder: {self.machine_trail_maps_folder or 'Not configured'}")
        print(f"Backup folder: {self.machine_backup_folder or 'Not configured'}")
        
        # Check config file
        json_config_path = self.get_json_config_path()
        if json_config_path and json_config_path.exists():
            print(f"Config file: {json_config_path}")
        else:
            print("Config file: Not found (using defaults)")
        
        # Check database
        if self.machine_db_path:
            db_file = Path(self.machine_db_path) / "air_scenting.db"
            if db_file.exists():
                print(f"Database file: {db_file} (exists)")
            else:
                print(f"Database file: {db_file} (does not exist)")
            
            # Check JSON folder
            json_folder = Path(self.machine_db_path) / "JSON"
            if json_folder.exists():
                print(f"Primary JSON folder: {json_folder} (exists)")
            else:
                print(f"Primary JSON folder: {json_folder} (does not exist)")
        
        # Check secondary JSON folder
        if self.machine_backup_folder:
            secondary_json = Path(self.machine_backup_folder) / "JSON"
            if secondary_json.exists():
                print(f"Secondary JSON folder: {secondary_json} (exists)")
            else:
                print(f"Secondary JSON folder: {secondary_json} (does not exist)")
        
        print("=" * 60)
        
        # Disable View/Edit/Hide and Export PDF buttons until startup is complete
        self._disable_sync_sensitive_buttons()
        
        # Check if database is healthy before deciding sync strategy
        db_healthy = self._check_db_health()
        
        if db_healthy:
            # DB is healthy - run sync in background thread
            self._start_startup_sync_thread()
        else:
            # DB is damaged - run sync synchronously to rebuild
            print("Database appears damaged - running synchronous rebuild...")
            self._perform_startup_sync()
            self._enable_sync_sensitive_buttons()
        
        # Load terrain types
        terrain_types = self.config.get("terrain_types", get_default_terrain_types())
        self.trailing_entry.update_terrain_types(terrain_types)
        
        # Load distraction types
        distraction_types = self.config.get("distraction_types", get_default_distraction_types())
        self.trailing_entry.update_distraction_types(distraction_types)
        
        # Load dogs - try database first, then config
        dog_names = []
        try:
            from database import get_connection
            from sqlalchemy import text
            with get_connection() as conn:
                result = conn.execute(text("SELECT name FROM dogs ORDER BY name"))
                dog_names = [row[0] for row in result]
                print(f"Loaded {len(dog_names)} dogs from database")
        except Exception as e:
            print(f"Could not load dogs from database: {e}")
            dog_names = self.config.get("dog_names", [])
            print(f"Using {len(dog_names)} dogs from config")
        
        self.trailing_entry.update_dog_list(dog_names)
        
        # Load locations - try database first, then config
        locations = []
        try:
            from database import get_connection
            from sqlalchemy import text
            with get_connection() as conn:
                result = conn.execute(text("SELECT name FROM training_locations ORDER BY name"))
                locations = [row[0] for row in result]
                print(f"Loaded {len(locations)} locations from database")
        except Exception as e:
            print(f"Could not load locations from database: {e}")
            locations = self.config.get("training_locations", [])
            print(f"Using {len(locations)} locations from config")
        
        self.trailing_entry.update_location_list(locations)
        
        # Set default handler
        default_handler = self.config.get("trailing", {}).get("default_handler", "")
        if default_handler:
            sv.t_handler.set(default_handler)
        
        # Set last dog
        last_dog = self.config.get("trailing", {}).get("last_dog", "")
        if last_dog and last_dog in dog_names:
            sv.t_dog.set(last_dog)
            # Get next session number
            next_session = self.get_next_session_number(last_dog)
            sv.t_session.set(str(next_session))
        
        sv.t_status.set("Ready" if not sv.sync_in_progress else "Synchronizing backups...")
        
        # Select Entry tab if database exists, otherwise stay on Setup tab
        if self.machine_db_path:
            db_file = Path(self.machine_db_path) / "air_scenting.db"
            if db_file.exists():
                self.notebook.select(self.entry_tab)
                print("Database found - starting on Entry tab")
    
    def _check_db_health(self) -> bool:
        """Check if database is accessible and has required tables."""
        try:
            from sqlalchemy import text
            from database import get_connection
            with get_connection() as conn:
                conn.execute(text("SELECT COUNT(*) FROM training_sessions"))
                conn.execute(text("SELECT COUNT(*) FROM t_training_sessions"))
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False
    
    def _disable_sync_sensitive_buttons(self):
        """Disable buttons that shouldn't be used during sync."""
        sv.sync_in_progress = True
        if hasattr(self, 'trailing_entry'):
            if hasattr(self.trailing_entry, 'view_edit_hide_btn'):
                self.trailing_entry.view_edit_hide_btn.config(state=tk.DISABLED)
            if hasattr(self.trailing_entry, 'export_pdf_btn'):
                self.trailing_entry.export_pdf_btn.config(state=tk.DISABLED)
    
    def _enable_sync_sensitive_buttons(self):
        """Re-enable buttons after sync completes."""
        sv.sync_in_progress = False
        if hasattr(self, 'trailing_entry'):
            if hasattr(self.trailing_entry, 'view_edit_hide_btn'):
                self.trailing_entry.view_edit_hide_btn.config(state=tk.NORMAL)
            if hasattr(self.trailing_entry, 'export_pdf_btn'):
                self.trailing_entry.export_pdf_btn.config(state=tk.NORMAL)
    
    def _start_startup_sync_thread(self):
        """Start startup sync in a background thread."""
        import threading
        from ui_utils import get_primary_json_folder, get_secondary_json_folder
        
        db_type = sv.db_type.get()
        primary_folder = get_primary_json_folder()
        secondary_folder = get_secondary_json_folder()
        
        if not primary_folder:
            print("Startup sync: No primary JSON folder configured, skipping")
            self._enable_sync_sensitive_buttons()
            return
        
        def do_sync():
            """Run sync in background thread"""
            try:
                from backup_sync import BackupSyncManager
                
                sync_manager = BackupSyncManager(
                    db_type=db_type,
                    primary_folder=primary_folder,
                    secondary_folder=secondary_folder
                )
                
                def status_callback(message):
                    def update():
                        sv.t_status.set(message)
                    self.root.after(0, update)
                
                results = sync_manager.perform_full_sync(status_callback=status_callback)
                
                def on_complete():
                    # Re-enable buttons
                    self._enable_sync_sensitive_buttons()
                    
                    # Update session number if DB was updated
                    db_updates = results.get('db_updates', 0)
                    if db_updates > 0:
                        dog_name = sv.t_dog.get()
                        if dog_name:
                            try:
                                next_session = self.get_next_session_number(dog_name)
                                sv.t_session.set(str(next_session))
                                print(f"Startup sync: Updated session number to {next_session} for {dog_name}")
                            except Exception as e:
                                print(f"Startup sync: Error updating session number: {e}")
                    
                    # Update status
                    total_changes = (
                        db_updates +
                        results.get('primary_writes', 0) +
                        results.get('secondary_writes', 0) +
                        results.get('renames', 0)
                    )
                    
                    if total_changes > 0:
                        self.show_status_message(f"Sync complete: {total_changes} file(s) synchronized", "info")
                    else:
                        sv.t_status.set("Ready")
                
                self.root.after(0, on_complete)
                
            except Exception as e:
                print(f"Startup sync error: {e}")
                import traceback
                traceback.print_exc()
                
                def reset():
                    self._enable_sync_sensitive_buttons()
                    sv.t_status.set("Ready")
                self.root.after(0, reset)
        
        # Start sync thread
        sync_thread = threading.Thread(target=do_sync, daemon=True)
        sync_thread.start()
        print("Startup sync: Started in background thread")
    
    def _perform_startup_sync(self):
        """Perform startup sync to ensure DB, primary, and secondary backups agree."""
        try:
            from backup_sync import BackupSyncManager
            from ui_utils import get_primary_json_folder, get_secondary_json_folder
            
            db_type = sv.db_type.get()
            primary_folder = get_primary_json_folder()
            secondary_folder = get_secondary_json_folder()
            
            if not primary_folder:
                print("Startup sync: No primary JSON folder configured, skipping")
                return
            
            print("Startup sync: Beginning synchronization...")
            sv.t_status.set("Synchronizing backups...")
            self.root.update_idletasks()
            
            sync_manager = BackupSyncManager(
                db_type=db_type,
                primary_folder=primary_folder,
                secondary_folder=secondary_folder
            )
            
            def status_callback(message):
                print(f"  {message}")
                sv.t_status.set(message)
                self.root.update_idletasks()
            
            results = sync_manager.perform_full_sync(status_callback=status_callback)
            
            total_changes = (
                results.get('db_updates', 0) +
                results.get('primary_writes', 0) +
                results.get('secondary_writes', 0) +
                results.get('renames', 0)
            )
            
            if total_changes > 0:
                print(f"Startup sync complete: {total_changes} change(s)")
                sv.t_status.set(f"Sync complete: {total_changes} file(s) synchronized")
            else:
                print("Startup sync complete: All backups already in sync")
                sv.t_status.set("All backups synchronized")
            
        except ImportError:
            print("Startup sync: backup_sync module not available, using legacy sync")
            # Fall back to legacy sync if new module not available
        except Exception as e:
            print(f"Startup sync error: {e}")
            import traceback
            traceback.print_exc()
    
    def _start_background_sync(self):
        """Start background sync between database and JSON backup folders.
        
        Uses the new backup_sync module for comprehensive synchronization.
        """
        import threading
        from ui_utils import get_primary_json_folder, get_secondary_json_folder
        
        try:
            db_type = sv.db_type.get()
            primary_folder = get_primary_json_folder()
            secondary_folder = get_secondary_json_folder()
            
            if not primary_folder:
                print("Sync: No primary JSON folder configured, skipping sync")
                return
            
            # Disable buttons during sync
            self._disable_sync_sensitive_buttons()
            
            def do_sync():
                """Run sync in background thread"""
                try:
                    from backup_sync import BackupSyncManager
                    
                    sync_manager = BackupSyncManager(
                        db_type=db_type,
                        primary_folder=primary_folder,
                        secondary_folder=secondary_folder
                    )
                    
                    def status_callback(message):
                        def update():
                            sv.t_status.set(message)
                        self.root.after(0, update)
                    
                    results = sync_manager.perform_full_sync(status_callback=status_callback)
                    
                    def update_ui():
                        # Re-enable buttons
                        self._enable_sync_sensitive_buttons()
                        
                        # Update session number if DB was updated
                        db_updates = results.get('db_updates', 0)
                        if db_updates > 0:
                            dog_name = sv.t_dog.get()
                            if dog_name:
                                try:
                                    next_session = self.get_next_session_number(dog_name)
                                    sv.t_session.set(str(next_session))
                                except Exception as e:
                                    print(f"Sync: Error updating session number: {e}")
                        
                        total_changes = (
                            db_updates +
                            results.get('primary_writes', 0) +
                            results.get('secondary_writes', 0)
                        )
                        
                        if total_changes > 0:
                            self.show_status_message(f"Sync complete: {total_changes} file(s) synchronized", "info")
                        else:
                            sv.t_status.set("Sync complete: All backups up to date")
                        
                        if results.get('errors'):
                            print(f"Sync errors: {results['errors']}")
                    
                    self.root.after(0, update_ui)
                    
                except Exception as e:
                    print(f"Background sync error: {e}")
                    def reset():
                        self._enable_sync_sensitive_buttons()
                    self.root.after(0, reset)
            
            # Start sync thread
            sync_thread = threading.Thread(target=do_sync, daemon=True)
            sync_thread.start()
            
            print("Sync: Background sync started")
            
        except Exception as e:
            print(f"Error starting background sync: {e}")
            self._enable_sync_sensitive_buttons()
    
    # Config provider methods for ui_trailing.py compatibility
    def get_handler_name(self):
        return self.config.get("trailing", {}).get("default_handler", "")
    
    def get_dog_names(self):
        return self.config.get("dog_names", [])
    
    def get_last_dog_name(self):
        return self.config.get("trailing", {}).get("last_dog", "")
    
    def get_terrain_types(self):
        return self.config.get("terrain_types", get_default_terrain_types())
    
    def get_distraction_types(self):
        return self.config.get("distraction_types", get_default_distraction_types())
    
    def get_training_locations(self):
        return self.config.get("training_locations", [])
    
    def on_closing(self):
        """Handle window close"""
        # Save last dog and handler
        current_dog = sv.t_dog.get()
        current_handler = sv.t_handler.get()
        
        if "trailing" not in self.config:
            self.config["trailing"] = {}
        
        if current_dog:
            self.config["trailing"]["last_dog"] = current_dog
        
        if current_handler:
            self.config["trailing"]["default_handler"] = current_handler
        
        self.save_config()
        self.root.destroy()
    
    # ===== STATUS BAR METHODS =====
    
    def show_status_message(self, message, msg_type="info"):
        """Display a status message with appropriate color and priority
        
        Args:
            message: Message text to display
            msg_type: "info", "warning", or "error"
        
        Uses StatusBarManager with 3 priority queues:
            - Error: Red flashing, highest priority
            - Warning: Orange text, medium priority
            - Info: Black text, lowest priority
        """
        self.status_bar_mgr.show_message(message, msg_type)
    
    def _flash_step(self):
        """Flash animation step - handled by StatusBarManager"""
        pass  # Now handled by StatusBarManager
    
    def _stop_flash(self):
        """Stop flash animation - handled by StatusBarManager"""
        self.status_bar_mgr._stop_flash()
    
    def dismiss_status_message(self, event=None):
        """Clear the current status message - wrapper for StatusBarManager"""
        self.status_bar_mgr.dismiss_message(event)
    
    def prev_status_message(self):
        """Navigate to previous (older) status message - wrapper for StatusBarManager"""
        self.status_bar_mgr.prev_message()
    
    def next_status_message(self):
        """Navigate to next (newer) status message - wrapper for StatusBarManager"""
        self.status_bar_mgr.next_message()
    
    def on_tab_changed(self, event):
        """Handle tab change event - check for setup requirements"""
        current_tab_index = self.notebook.index(self.notebook.select())
        
        # Check if we're leaving the Setup tab (index 0)
        if self.previous_tab_index == 0 and current_tab_index != 0:
            # Check if database exists before allowing tab switch
            if not self.check_setup_requirements():
                # Requirements not met - stay on Setup tab
                self.notebook.select(self.setup_tab)
                self.previous_tab_index = 0
                return
        
        # Update previous tab index
        self.previous_tab_index = current_tab_index
    
    def check_setup_requirements(self):
        """Check if database exists before leaving Setup tab"""
        db_type = sv.db_type.get()
        
        # For SQLite, check if database file exists
        if db_type == "sqlite":
            import config as config_module
            db_url = config_module.DB_CONFIG.get("sqlite", {}).get("url", "")
            db_path = db_url.replace("sqlite:///", "")
            if not db_path or not os.path.exists(db_path):
                messagebox.showwarning(
                    "Database Required",
                    "Please create or select a database before continuing.\n\n"
                    "Use the 'Create Database' button to create a new database,\n"
                    "or browse to select an existing database file."
                )
                return False
            
            # Check if tables exist
            try:
                from sqlalchemy import text
                from database import get_connection
                with get_connection() as conn:
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='t_training_sessions'"))
                    if not result.fetchone():
                        messagebox.showwarning(
                            "Database Not Initialized",
                            "The database exists but has not been initialized.\n\n"
                            "Please click 'Create Database' to initialize the database tables."
                        )
                        return False
            except Exception as e:
                messagebox.showwarning(
                    "Database Error",
                    f"Could not verify database: {str(e)}\n\n"
                    "Please check your database configuration."
                )
                return False
        
        # For network databases, check connection
        elif db_type in ["postgres", "supabase", "mysql"]:
            try:
                from sqlalchemy import text
                from database import get_connection
                with get_connection() as conn:
                    conn.execute(text("SELECT 1"))
            except Exception as e:
                messagebox.showwarning(
                    "Database Connection Failed",
                    f"Could not connect to the database.\n\n"
                    f"Error: {str(e)}\n\n"
                    "Please check your database configuration and credentials."
                )
                return False
        
        # Check backup folder - soft warning only
        backup_folder = sv.backup_folder.get().strip()
        if not backup_folder or not os.path.exists(backup_folder):
            if not backup_folder:
                warning_detail = "Secondary backup folder not selected"
            else:
                warning_detail = f"Secondary backup folder does not exist: {backup_folder}"
            
            warning_msg = f"Secondary Backup Warning\n\n{warning_detail}\n\n"
            warning_msg += "Session data will be saved to the primary database, but "
            warning_msg += "secondary JSON backups will not be created.\n\n"
            warning_msg += "Do you want to continue anyway?"
            
            self.show_status_message("Secondary backup folder not configured", "warning")
            
            result = messagebox.askquestion("Backup Warning", warning_msg, icon='warning')
            if result == 'no':
                return False
        
        return True
    
    def _update_arrow_states(self):
        """Update arrow button states - wrapper for StatusBarManager"""
        self.status_bar_mgr._update_arrow_states()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = TrailingUI()
    app.run()
