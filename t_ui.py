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
        self.machine_db_path = ""
        self.machine_trail_maps_folder = ""
        self.machine_backup_folder = ""
        
        # Load paths from bootstrap if exists
        self.load_bootstrap()
        
        # CRITICAL: Update database path in the shared config module BEFORE any database operations
        # database.py imports config (not t_config), so we must update the original config
        import config as original_config
        if self.machine_db_path:
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
        
        self.root.withdraw()
        
        # Show splash screen
        self.splash = SplashScreen(self.root, version="1.0.0-alpha", 
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
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
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
        
        # Message history for status bar
        self.status_message_history = []
        self.status_message_index = -1
        self.max_status_messages = 5
        
        # Error handling flags
        self.error_showing = False
        self.is_flashing = False
        self.flash_after_id = None
        
        # Status bar frame at bottom
        status_bar_frame = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Left arrow button for message history
        self.status_left_arrow = tk.Button(status_bar_frame, text="◀", 
                                           width=2, state="disabled",
                                           command=self.prev_status_message)
        self.status_left_arrow.pack(side=tk.LEFT, padx=(2, 0))
        
        # Right arrow button for message history
        self.status_right_arrow = tk.Button(status_bar_frame, text="▶", 
                                            width=2, state="disabled",
                                            command=self.next_status_message)
        self.status_right_arrow.pack(side=tk.LEFT, padx=(2, 0))
        
        # Cancel button to dismiss message
        self.status_cancel_button = tk.Button(status_bar_frame, text="Cancel Msg", 
                                              width=10, 
                                              command=self.dismiss_status_message,
                                              relief=tk.RAISED,
                                              cursor="hand2")
        self.status_cancel_button.pack(side=tk.LEFT, padx=(5, 2))
        
        # Status message label
        self.status_label = tk.Label(status_bar_frame, textvariable=sv.t_status,
                                     anchor=tk.W, padx=5, pady=2)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Bind click to dismiss message
        self.status_label.bind("<Button-1>", self.dismiss_status_message)
        
        # Show main window
        self.root.deiconify()
        self.root.update()
        
        # Load initial data
        self.root.after(500, self.load_initial_data)
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_bootstrap(self):
        """Load machine-specific paths from bootstrap file"""
        if self.bootstrap_file.exists():
            try:
                with open(self.bootstrap_file, 'r') as f:
                    bootstrap = json.load(f)
                    self.machine_db_path = bootstrap.get("db_file_path", "")
                    self.machine_trail_maps_folder = bootstrap.get("trail_maps_folder", "")
                    self.machine_backup_folder = bootstrap.get("backup_folder", "")
            except:
                pass
    
    def save_bootstrap(self):
        """Save machine-specific paths to bootstrap file"""
        bootstrap = {"config_folder_path": str(self.config_file.parent)}
        if self.bootstrap_file.exists():
            try:
                with open(self.bootstrap_file, 'r') as f:
                    bootstrap = json.load(f)
            except:
                pass
        
        bootstrap["db_file_path"] = self.machine_db_path
        bootstrap["trail_maps_folder"] = self.machine_trail_maps_folder
        bootstrap["backup_folder"] = self.machine_backup_folder
        
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
        show_about(self.root, version="1.0.0-alpha", 
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
            
            # Clear form and set up for next session (unless editing)
            if not is_update:
                self.trailing_entry.clear_form()
            else:
                # If editing, reset editing mode but keep current session displayed
                self.trailing_entry.editing_session = False
                self.trailing_entry.editing_row = None
            
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
            print(f"Warning: Failed to save trailing session to JSON: {e}")
    
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
    
    def on_export_pdf(self):
        """Export sessions to PDF with range and status options"""
        from tkinter import Toplevel
        from tkcalendar import DateEntry
        
        dog_name = sv.t_dog.get()
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first.")
            return
        
        # Create dialog
        dialog = Toplevel(self.root)
        dialog.title("Export Sessions to PDF")
        dialog.geometry("500x420")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        # Dog display
        tk.Label(frame, text="Dog:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        tk.Label(frame, text=dog_name, font=("Helvetica", 10)).grid(row=0, column=1, sticky="w", pady=(0, 10))
        
        # Range type selection
        tk.Label(frame, text="Export Range:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(10, 5))
        
        range_type_var = tk.StringVar(value="Date")
        tk.Radiobutton(frame, text="Date Range", variable=range_type_var, value="Date").grid(row=2, column=0, sticky="w", padx=(20, 0))
        tk.Radiobutton(frame, text="Session Number Range", variable=range_type_var, value="Session").grid(row=3, column=0, sticky="w", padx=(20, 0))
        
        # Range inputs frame
        input_frame = tk.Frame(frame)
        input_frame.grid(row=2, column=1, rowspan=2, sticky="w", padx=(20, 0))
        
        # Get min/max values
        db_ops = DatabaseOperations(self)
        
        def get_dog_ranges():
            try:
                from database import get_connection
                from sqlalchemy import text
                with get_connection() as conn:
                    result = conn.execute(text("""
                        SELECT MIN(t_date), MAX(t_date), MIN(t_session_number), MAX(t_session_number)
                        FROM t_training_sessions WHERE t_dog_name = :dog_name
                    """), {"dog_name": dog_name})
                    row = result.fetchone()
                    return row[0], row[1], row[2], row[3]
            except:
                return None, None, None, None
        
        min_date, max_date, min_session, max_session = get_dog_ranges()
        
        # Labels
        tk.Label(input_frame, text="Start:").grid(row=0, column=0, sticky="e", padx=5)
        tk.Label(input_frame, text="End:").grid(row=1, column=0, sticky="e", padx=5)
        
        # Date pickers
        start_date = DateEntry(input_frame, width=14, date_pattern='yyyy-mm-dd')
        start_date.grid(row=0, column=1, padx=5, pady=2)
        end_date = DateEntry(input_frame, width=14, date_pattern='yyyy-mm-dd')
        end_date.grid(row=1, column=1, padx=5, pady=2)
        
        # Session entries
        start_var = tk.StringVar(value=str(min_session) if min_session else "1")
        end_var = tk.StringVar(value=str(max_session) if max_session else "1")
        start_entry = tk.Entry(input_frame, textvariable=start_var, width=15)
        end_entry = tk.Entry(input_frame, textvariable=end_var, width=15)
        
        def update_input_widgets(*args):
            if range_type_var.get() == "Date":
                start_date.grid(row=0, column=1, padx=5, pady=2)
                end_date.grid(row=1, column=1, padx=5, pady=2)
                start_entry.grid_remove()
                end_entry.grid_remove()
            else:
                start_entry.grid(row=0, column=1, padx=5, pady=2)
                end_entry.grid(row=1, column=1, padx=5, pady=2)
                start_date.grid_remove()
                end_date.grid_remove()
        
        range_type_var.trace("w", update_input_widgets)
        update_input_widgets()
        
        # Status filter
        tk.Label(frame, text="Session Status:", font=("Helvetica", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(15, 5))
        status_frame = tk.Frame(frame)
        status_frame.grid(row=4, column=1, sticky="w", pady=(15, 5))
        
        status_var = tk.StringVar(value="active")
        tk.Radiobutton(status_frame, text="Active", variable=status_var, value="active").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(status_frame, text="Hidden", variable=status_var, value="deleted").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(status_frame, text="Both", variable=status_var, value="both").pack(side=tk.LEFT, padx=5)
        
        # Sort order
        tk.Label(frame, text="Sort Order:", font=("Helvetica", 10, "bold")).grid(row=5, column=0, sticky="w", pady=(15, 5))
        sort_var = tk.StringVar(value="Ascending")
        ttk.Combobox(frame, textvariable=sort_var, width=20, state="readonly", 
                     values=["Ascending", "Descending"]).grid(row=5, column=1, sticky="w", pady=(15, 5))
        
        # Buttons
        button_frame = tk.Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))
        
        def do_export():
            # Get range values
            if range_type_var.get() == "Date":
                start_value = start_date.get_date().strftime("%Y-%m-%d")
                end_value = end_date.get_date().strftime("%Y-%m-%d")
            else:
                start_value = start_var.get()
                end_value = end_var.get()
            
            if not start_value or not end_value:
                messagebox.showwarning("Invalid Range", "Please enter both start and end values")
                return
            
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
            
            # Export
            self._export_trailing_sessions_to_pdf(
                filepath, dog_name, range_type_var.get(),
                start_value, end_value, sort_var.get(), status_var.get()
            )
        
        tk.Button(button_frame, text="Export to PDF", command=do_export, bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
    
    def _export_trailing_sessions_to_pdf(self, filepath, dog_name, range_type, start_value, end_value, sort_order, status_filter):
        """Export multiple trailing sessions to PDF file"""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        try:
            # Fetch sessions
            db_ops = DatabaseOperations(self)
            sessions = db_ops.get_trailing_sessions_for_export(
                dog_name, range_type, start_value, end_value, sort_order, status_filter
            )
            
            if not sessions:
                messagebox.showinfo("No Sessions", "No sessions found matching the specified criteria")
                return
            
            doc = SimpleDocTemplate(filepath, pagesize=letter, 
                                    rightMargin=0.5*inch, leftMargin=0.5*inch,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=20)
            heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], spaceAfter=10, spaceBefore=15)
            
            elements = []
            
            for i, session_data in enumerate(sessions):
                if i > 0:
                    elements.append(PageBreak())
                
                # Title
                session_num = session_data.get('t_session_number', '?')
                elements.append(Paragraph(f"Trailing Session Report", title_style))
                elements.append(Paragraph(f"{dog_name} - Session #{session_num}", styles['Heading2']))
                elements.append(Spacer(1, 0.2*inch))
                
                # Session Information
                elements.append(Paragraph("Session Information", heading_style))
                session_info = [
                    ['Date:', str(session_data.get('t_date', '')), 'Handler:', session_data.get('t_handler', '')],
                    ['Location:', session_data.get('t_location', ''), 'Field Support:', session_data.get('t_field_support', '')],
                    ['Start Time:', session_data.get('t_start_time', ''), 'Finish Time:', session_data.get('t_finish_time', '')],
                ]
                t = Table(session_info, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(t)
                
                # Trail Information
                elements.append(Paragraph("Trail Information", heading_style))
                trail_info = [
                    ['Trail Age:', session_data.get('t_trail_age', ''), 'Trail Length:', session_data.get('t_trail_length', '')],
                    ['Difficulty:', session_data.get('t_difficulty', ''), 'Trail Layer:', session_data.get('t_trail_layer', '')],
                ]
                t = Table(trail_info, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(t)
                
                # Impression
                impression = session_data.get('t_impression', '')
                if impression:
                    elements.append(Paragraph("Overall Impression", heading_style))
                    elements.append(Paragraph(str(impression), styles['Normal']))
            
            doc.build(elements)
            
            messagebox.showinfo("Success", f"Exported {len(sessions)} session(s) to:\n{filepath}")
            
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
        """Show a status message with optional type (info, warning, error)"""
        # Stop any existing flash
        self._stop_flash()
        
        # Add to history
        self.status_message_history.append((message, msg_type))
        if len(self.status_message_history) > self.max_status_messages:
            self.status_message_history.pop(0)
        
        # Reset to most recent
        self.status_message_index = -1
        
        # Set the message
        sv.t_status.set(message)
        
        # Set colors based on type
        if msg_type == "error":
            self.error_showing = True
            self.is_flashing = True
            self.flash_state = False
            self.root.after(100, self._flash_step)
        elif msg_type == "warning":
            self.error_showing = False
            self.status_label.config(fg="orange", bg="SystemButtonFace", font=("TkDefaultFont", 9, "normal"))
        else:
            self.error_showing = False
            self.status_label.config(fg="black", bg="SystemButtonFace", font=("TkDefaultFont", 9, "normal"))
        
        self._update_arrow_states()
    
    def _flash_step(self):
        """Animate error flashing"""
        if not self.is_flashing:
            return
        
        self.flash_state = not self.flash_state
        if self.flash_state:
            self.status_label.config(fg="white", bg="red", font=("TkDefaultFont", 9, "bold"))
        else:
            self.status_label.config(fg="red", bg="SystemButtonFace", font=("TkDefaultFont", 9, "bold"))
        
        self.flash_after_id = self.root.after(500, self._flash_step)
    
    def _stop_flash(self):
        """Stop flashing animation"""
        self.is_flashing = False
        if self.flash_after_id:
            self.root.after_cancel(self.flash_after_id)
            self.flash_after_id = None
        self.status_label.config(fg="black", bg="SystemButtonFace", font=("TkDefaultFont", 9, "normal"))
    
    def dismiss_status_message(self, event=None):
        """Clear the current status message"""
        self._stop_flash()
        self.error_showing = False
        
        if self.status_message_history and self.status_message_index >= 0:
            actual_index = -(self.status_message_index + 1)
            if -actual_index <= len(self.status_message_history):
                self.status_message_history.pop(actual_index)
                
                if self.status_message_history:
                    if self.status_message_index >= len(self.status_message_history):
                        self.status_message_index = len(self.status_message_history) - 1
                    message, msg_type = self.status_message_history[-(self.status_message_index + 1)]
                    sv.t_status.set(message)
                else:
                    self.status_message_index = -1
                    sv.t_status.set("")
            else:
                sv.t_status.set("")
        elif self.status_message_history and self.status_message_index == -1:
            self.status_message_history.pop()
            if self.status_message_history:
                message, msg_type = self.status_message_history[-1]
                sv.t_status.set(message)
            else:
                sv.t_status.set("")
        else:
            sv.t_status.set("")
        
        self._update_arrow_states()
    
    def prev_status_message(self):
        """Navigate to previous (older) status message"""
        if not self.status_message_history:
            return
        
        if self.error_showing and self.status_message_index == -1:
            return
        
        if self.status_message_index == -1:
            if len(self.status_message_history) >= 2:
                self.status_message_index = 1
                message, msg_type = self.status_message_history[-2]
                sv.t_status.set(message)
                self._update_arrow_states()
            return
        
        if self.status_message_index < len(self.status_message_history) - 1:
            self.status_message_index += 1
            message, msg_type = self.status_message_history[-(self.status_message_index + 1)]
            sv.t_status.set(message)
            self._update_arrow_states()
    
    def next_status_message(self):
        """Navigate to next (newer) status message"""
        if not self.status_message_history:
            return
        
        if self.error_showing and self.status_message_index == -1:
            return
        
        if self.status_message_index > 0:
            self.status_message_index -= 1
            message, msg_type = self.status_message_history[-(self.status_message_index + 1)]
            sv.t_status.set(message)
            self._update_arrow_states()
        elif self.status_message_index == 0:
            self.status_message_index = -1
            if self.status_message_history:
                message, msg_type = self.status_message_history[-1]
                sv.t_status.set(message)
            self._update_arrow_states()
    
    def _update_arrow_states(self):
        """Update arrow button states based on history position"""
        if not self.status_message_history:
            self.status_left_arrow.config(state="disabled")
            self.status_right_arrow.config(state="disabled")
            return
        
        if self.error_showing and self.status_message_index == -1:
            self.status_left_arrow.config(state="disabled")
            self.status_right_arrow.config(state="disabled")
            return
        
        history_len = len(self.status_message_history)
        
        if self.status_message_index == -1:
            if history_len >= 2:
                self.status_left_arrow.config(state="normal")
            else:
                self.status_left_arrow.config(state="disabled")
            self.status_right_arrow.config(state="disabled")
        else:
            if self.status_message_index < history_len - 1:
                self.status_left_arrow.config(state="normal")
            else:
                self.status_left_arrow.config(state="disabled")
            self.status_right_arrow.config(state="normal")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = TrailingUI()
    app.run()
