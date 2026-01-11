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
        """Save trailing session to JSON backup file"""
        from ui_utils import save_json_mirrored
        
        try:
            # Build the backup data
            backup_data = {
                **session_data,
                "selected_terrains": terrains,
                "selected_purposes": purposes,
                "distractions": distractions,
                "user_name": get_username(),
                "backup_time": datetime.now().isoformat()
            }
            
            # Create filename: t_session_<dog>_<session>.json
            dog_name = session_data.get('t_dog_name', 'unknown').replace(' ', '_')
            session_num = session_data.get('t_session_number', '0')
            filename = f"t_session_{dog_name}_{session_num}.json"
            
            primary, secondary = save_json_mirrored(filename, backup_data)
            
            if primary:
                print(f"Trailing session saved to JSON: {primary}")
            if secondary:
                print(f"Trailing session mirrored to: {secondary}")
                
        except Exception as e:
            print(f"Warning: Failed to save trailing session to JSON: {e}")
    
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
        """Export current session to PDF"""
        from tkinter import filedialog
        
        # Check if a session is loaded
        if not sv.t_session.get() or sv.t_session.get() == "":
            messagebox.showwarning("No Session", "Please load a session to export.")
            return
        
        # Get current session data from form
        session_data = self.trailing_entry.get_session_data()
        dog_name = sv.t_dog.get()
        session_num = sv.t_session.get()
        
        # Ask for save location
        default_filename = f"trailing_session_{dog_name}_{session_num}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_filename,
            title="Export Session to PDF"
        )
        
        if not filepath:
            return
        
        try:
            self._export_session_to_pdf(filepath, session_data)
            self.show_status_message(f"PDF exported: {filepath}", "info")
            
            # Ask if user wants to open the file
            if messagebox.askyesno("Export Complete", "PDF exported successfully!\n\nWould you like to open it?"):
                import subprocess
                import platform
                if platform.system() == 'Windows':
                    os.startfile(filepath)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', filepath])
                else:  # Linux
                    subprocess.run(['xdg-open', filepath])
                    
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export PDF:\n{e}")
            print(f"PDF export error: {e}")
            import traceback
            traceback.print_exc()
    
    def _export_session_to_pdf(self, filepath, session_data):
        """Export a trailing session to PDF file"""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        doc = SimpleDocTemplate(filepath, pagesize=letter, 
                                rightMargin=0.5*inch, leftMargin=0.5*inch,
                                topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=20)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], spaceAfter=10, spaceBefore=15)
        
        elements = []
        
        # Title
        dog_name = session_data.get('t_dog_name', 'Unknown')
        session_num = session_data.get('t_session_number', '?')
        elements.append(Paragraph(f"Trailing Session Report", title_style))
        elements.append(Paragraph(f"{dog_name} - Session #{session_num}", styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Session Information
        elements.append(Paragraph("Session Information", heading_style))
        session_info = [
            ['Date:', session_data.get('t_date', ''), 'Handler:', session_data.get('t_handler', '')],
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
            ['Cross Track:', session_data.get('t_cross_track_layer', ''), 'Cross Track Age:', session_data.get('t_cross_track_age', '')],
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
        
        # Weather - Laying Trail
        elements.append(Paragraph("Weather When Laying Trail", heading_style))
        weather_laying = [
            ['Weather:', session_data.get('t_weather_laying', ''), 'Temperature:', session_data.get('t_temperature_laying', '')],
            ['Wind Speed:', session_data.get('t_wind_speed_laying', ''), 'Wind Direction:', session_data.get('t_wind_direction_laying', '')],
            ['Humidity:', session_data.get('t_humidity_laying', ''), '', ''],
        ]
        t = Table(weather_laying, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        
        # Weather - Running Trail
        elements.append(Paragraph("Weather When Running Trail", heading_style))
        weather_running = [
            ['Weather:', session_data.get('t_weather_running', ''), 'Temperature:', session_data.get('t_temperature_running', '')],
            ['Wind Speed:', session_data.get('t_wind_speed_running', ''), 'Wind Direction:', session_data.get('t_wind_direction_running', '')],
            ['Humidity:', session_data.get('t_humidity_running', ''), '', ''],
        ]
        t = Table(weather_running, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        
        # Behavior/Performance
        elements.append(Paragraph("Behavior & Performance", heading_style))
        behavior = [
            ['Start Behavior:', session_data.get('t_start_behavior', ''), 'Consistency:', session_data.get('t_consistency', '')],
            ['Head Position:', session_data.get('t_head_position', ''), 'Pace:', session_data.get('t_pace', '')],
            ['Indication:', session_data.get('t_indication', ''), '', ''],
            ['Time to Complete:', session_data.get('t_time_to_complete', ''), 'Success Rate:', session_data.get('t_success_rate', '')],
        ]
        t = Table(behavior, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        
        # Overall Impression
        impression = session_data.get('t_impression', '')
        if impression:
            elements.append(Paragraph("Overall Impression", heading_style))
            elements.append(Paragraph(impression, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
    
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
        
        sv.t_status.set("Ready")
        
        # Select Entry tab if database exists, otherwise stay on Setup tab
        if self.machine_db_path:
            db_file = Path(self.machine_db_path) / "air_scenting.db"
            if db_file.exists():
                self.notebook.select(self.entry_tab)
                print("Database found - starting on Entry tab")
                
                # Start background sync
                self.root.after(500, self._start_background_sync)
    
    def _start_background_sync(self):
        """Start background sync between database and JSON backup folders."""
        from backup_management import get_sync_manager
        from ui_utils import get_primary_json_folder, get_secondary_json_folder
        
        try:
            db_type = sv.db_type.get()
            primary_folder = get_primary_json_folder()
            secondary_folder = get_secondary_json_folder()
            
            if not primary_folder:
                print("Sync: No primary JSON folder configured, skipping sync")
                return
            
            sync_manager = get_sync_manager()
            
            # Set flag to block operations during sync
            sv.sync_in_progress = True
            
            def on_sync_complete(results):
                """Called when sync finishes (on background thread)"""
                def update_ui():
                    sv.sync_in_progress = False
                    
                    # Build status message
                    total_changes = (
                        results.get("db_to_json", 0) +
                        results.get("json_to_db", 0) +
                        results.get("primary_to_secondary", 0) +
                        results.get("secondary_to_primary", 0)
                    )
                    
                    if total_changes > 0:
                        self.show_status_message(f"Sync complete: {total_changes} file(s) synchronized", "info")
                    else:
                        sv.t_status.set("Sync complete: All backups up to date")
                    
                    if results.get("errors"):
                        print(f"Sync errors: {results['errors']}")
                
                self.root.after(0, update_ui)
            
            def status_callback(message):
                """Update status bar during sync"""
                def update():
                    sv.t_status.set(message)
                self.root.after(0, update)
            
            # Start sync
            sync_manager.start_background_sync(
                db_type=db_type,
                primary_folder=str(primary_folder) if primary_folder else None,
                secondary_folder=str(secondary_folder) if secondary_folder else None,
                on_complete=on_sync_complete,
                status_callback=status_callback
            )
            
            print("Sync: Background sync started")
            
        except Exception as e:
            print(f"Error starting background sync: {e}")
            sv.sync_in_progress = False
    
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
