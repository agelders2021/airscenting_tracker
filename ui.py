"""
UI Module for Air-Scenting Logger
Contains all tkinter interface code
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkcalendar import DateEntry
import json
import os
from pathlib import Path
from datetime import datetime
from getpass import getuser
from config import APP_TITLE, CONFIG_FILE, BOOTSTRAP_FILE
from splash_screen import SplashScreen
from ui_file_operations import FileOperations
from ui_misc2 import Misc2Operations
from setup_tab import SetupTab
from ui_form_management import FormManagement
from ui_navigation import Navigation
from ui_database import DatabaseOperations
from ui_file_operations import FileOperations
from about_dialog import show_about
from tips import ToolTip, ConditionalToolTip
from ui_utils import get_username, get_default_terrain_types, get_default_distraction_types
from ui_database import get_db_manager
from ui_misc_data_ops import MiscDataOperations
from working_dialog import WorkingDialog, run_with_working_dialog
import sv  # Import sv module (not 'from sv import sv')
from ui_database import get_db_manager
from ui_misc_data_ops import MiscDataOperations


class AirScentingUI:
    """Main UI class for Air-Scenting Logger"""
    
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
        
        # Load config
        self.config = self.load_config()
        
        # Create main window and withdraw it while splash is showing
        # Use TkinterDnD.Tk() instead of tk.Tk() for drag-and-drop support
        self.root = TkinterDnD.Tk()
        # Initialize sv module with the root window
        # This must be done AFTER root is created but BEFORE any sv usage
        sv.initialize(self.root)
        sv.db_type.set(self.config.get("db_type","sqlite")) # Added by ahg.
        # Load saved password immediately for networked databases
        if sv.db_type.get() in ["postgres", "supabase", "mysql"]:
            from password_manager import get_decrypted_password, check_crypto_available
            if check_crypto_available():
                saved_password = get_decrypted_password(self.config, sv.db_type.get())
                if saved_password:
                    sv.db_password.set(saved_password)
        
        # Initialize file operations module
        self.file_ops = FileOperations(self)
        self.form_mgmt = FormManagement(self)
        self.navigation = Navigation(self)
        self.misc_data_ops = MiscDataOperations(self)
        self.misc2_ops = Misc2Operations(self)
        self.setup_tab_mgr = SetupTab(self)
        
        """
        # Initialize file operations module
        #self.file_ops = FileOperations(self)
        
        # Initialize sv module with the root window
        # This must be done AFTER root is created but BEFORE any sv usage
        sv.initialize(self.root)
        # Load saved password immediately for networked databases
        if sv.db_type.get() in ["postgres", "supabase", "mysql"]:
            from password_manager import get_decrypted_password, check_crypto_available
            if check_crypto_available():
                saved_password = get_decrypted_password(self.config, sv.db_type.get())
                if saved_password:
                    sv.db_password.set(saved_password)
        """

        #sv.db_type.set(self.config.get("db_type","sqlite")) # Added by ahg.

        
        # Load bootstrap values into sv
        sv.db_path.set(self.machine_db_path)
        sv.trail_maps_folder.set(self.machine_trail_maps_folder)
        sv.backup_folder.set(self.machine_backup_folder)
        
        self.root.withdraw()
        
        # Show splash screen IMMEDIATELY (before building UI)
        # This ensures user sees progress while UI is being constructed
        # Splash will auto-close after 15 seconds or user can close it manually
        self.splash = SplashScreen(self.root, version="1.0.0-alpha")
        
        # Set window properties and center horizontally
        self.root.title(APP_TITLE)
        
        # Set initial window size (center horizontally, keep at top vertically)
        window_width = 1140
        window_height = 880
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Check if screen is too small for the window (leave space for taskbar)
        taskbar_margin = 100  # Space for taskbar/menu bar
        available_height = screen_height - taskbar_margin
        
        # Track if we need to maximize
        self.is_maximized = False
        
        if available_height < window_height:
            # Screen too small - maximize window
            self.is_maximized = True
            # Set geometry first, then maximize (works better on some systems)
            x_position = (screen_width - window_width) // 2
            self.root.geometry(f"{window_width}x{window_height}+{x_position}+0")
            
            # Maximize based on OS
            try:
                if os.name == 'nt':  # Windows
                    self.root.state('zoomed')
                else:  # Mac/Linux
                    # Try different methods
                    try:
                        self.root.attributes('-zoomed', True)
                    except:
                        # Fallback: set to screen size minus margin
                        self.root.geometry(f"{screen_width}x{available_height}+0+0")
            except Exception as e:
                print(f"Could not maximize window: {e}")
                # Fallback: fit to available height
                adjusted_height = min(window_height, available_height)
                x_position = max(0, (screen_width - window_width) // 2)
                self.root.geometry(f"{window_width}x{adjusted_height}+{x_position}+0")
        else:
            # Screen is large enough - use normal sizing
            # Calculate center position (horizontally centered, at top)
            x_position = (screen_width - window_width) // 2
            y_position = 0  # Keep at top of screen
            
            # Ensure window is not off-screen
            x_position = max(0, x_position)
            
            self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        self.root.minsize(window_width, 800)  # Minimum height slightly less than default
        
        # Create menu bar
        self.create_menu_bar()
        
        # Initialize path variables
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
        self.notebook.add(self.entry_tab, text="Training Session Entry")
        
        # Setup the tabs
        self.setup_setup_tab()
        self.setup_entry_tab()
        
        # Select initial tab based on database existence
        self.root.after(250,self.misc_data_ops.select_initial_tab)
        
        # Status bar at bottom (create before using it below)
        status_bar = tk.Label(self.root, textvariable=sv.status, 
                            bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Schedule session number update AFTER password is loaded (happens at 100ms)
        # This prevents database calls before authentication is ready
        def update_initial_session():
            loaded_dog = sv.dog.get()
            if loaded_dog:
                next_session = DatabaseOperations(self).get_next_session_number(loaded_dog)
                sv.session_number.set(str(next_session))
                sv.status.set(f"Ready - {loaded_dog} - Next session: #{next_session}")
                # Update navigation button states
                self.navigation.update_navigation_buttons()
        
        # Delay until after password AND database data are loaded
        # Password: 100ms, Database data: 500ms, Session update: 600ms
        self.root.after(600, update_initial_session)
        
        # Track form state for unsaved changes detection
        self.form_snapshot = ""
        
        # Show main window (splash will be on top due to topmost attribute)

        # Take initial snapshot of form state (after defaults loaded)
        # This prevents false "unsaved changes" when default handler is used
        self.root.after(200, self.form_mgmt.take_form_snapshot)
        self.root.deiconify()
        
        # CRITICAL: Force event loop to start processing
        # This allows splash screen countdown to begin immediately
        self.root.update()
        
        # Schedule initial database loading AFTER password is loaded
        # Password loads at 100ms (on_db_type_changed), so we wait until 500ms
        # This allows event loop to run and splash countdown to animate
        self.root.after(500, self.misc_data_ops.load_initial_database_data)
        
        # Take initial snapshot after UI is ready
        self.root.after(100, self.form_mgmt.take_form_snapshot)
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_date_changed(self, event=None):
        """Called when date picker value changes"""
        selected_date = self.a_date_picker.get_date()
        sv.date.set(selected_date.strftime("%Y-%m-%d"))
    
    def set_date(self, date_string):
        """Set the date in both date_var and date_picker widget"""
        try:
            # Parse the date string
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            # Update the DateEntry widget
            self.a_date_picker.set_date(date_obj)
            # Update the StringVar
            sv.date.set(date_string)
        except ValueError:
            # If invalid date, use today
            today = datetime.now()
            self.a_date_picker.set_date(today)
            sv.date.set(today.strftime("%Y-%m-%d"))
            
    def on_dog_changed(self, event=None):
        """Dog selection changed - delegate to Misc2Operations"""
        self.misc2_ops.on_dog_changed(event)
    
    def save_session(self):
        """Delegate to Misc2Operations"""
        return self.misc2_ops.save_session()
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
        # Get existing bootstrap data
        bootstrap = {"config_folder_path": str(self.config_file.parent)}
        if self.bootstrap_file.exists():
            try:
                with open(self.bootstrap_file, 'r') as f:
                    bootstrap = json.load(f)
            except:
                pass
        
        # Update with current machine paths
        bootstrap["db_file_path"] = self.machine_db_path
        bootstrap["trail_maps_folder"] = self.machine_trail_maps_folder
        bootstrap["backup_folder"] = self.machine_backup_folder
        
        # Save to bootstrap file
        with open(self.bootstrap_file, 'w') as f:
            json.dump(bootstrap, f, indent=2)
    
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
        show_about(self.root, version="1.0.0-alpha")
    
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "handler_name": "",
            "last_handler_name": "",
            "terrain_types": get_default_terrain_types(),
            "distraction_types": get_default_distraction_types(),
            "training_locations": [],
            "db_type": "sqlite"  # Default database type
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved = json.load(f)
                    # Add terrain_types if not present
                    if "terrain_types" not in saved:
                        saved["terrain_types"] = get_default_terrain_types()
                    # Add distraction_types if not present
                    if "distraction_types" not in saved:
                        saved["distraction_types"] = get_default_distraction_types()
                    # Add training_locations if not present
                    if "training_locations" not in saved:
                        saved["training_locations"] = []
                    default_config.update(saved)
            except:
                pass
        
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_setup_tab(self):
        """Setup the Setup tab - delegate to SetupTab module"""
        self.setup_tab_mgr.setup_setup_tab()
    
    def setup_entry_tab(self):
        """Setup the Training Session Entry tab"""
        # Create scrollable frame
        canvas = tk.Canvas(self.entry_tab)
        scrollbar = ttk.Scrollbar(self.entry_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        frame = tk.Frame(scrollable_frame, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        # Session Information
        session_frame = tk.LabelFrame(frame, text="Session Information", padx=10, pady=5)
        session_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Row 0: Date, Session #, and action buttons
        tk.Label(session_frame, text="Date:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        # Use DateEntry for date picker
        self.a_date_picker = DateEntry(
            session_frame,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day
        )
        self.a_date_picker.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        # Create StringVar to track the date for compatibility with existing code
        # Bind date picker changes to update the StringVar
        self.a_date_picker.bind("<<DateEntrySelected>>", self.on_date_changed)
        
        tk.Label(session_frame, text="Session #:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        # Initialize with "1" for now, will update after password is loaded
        self.a_session_entry = tk.Entry(session_frame, textvariable=sv.session_number, width=10)
        self.a_session_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        self.a_session_entry.bind("<FocusOut>", self.navigation.on_session_number_changed)
        self.a_session_entry.bind("<Return>", self.navigation.on_session_number_changed)
        tk.Button(session_frame, text="New", command=self.form_mgmt.new_session).grid(row=0, column=4, padx=5)
        
        tk.Button(session_frame, text="Edit/Delete Prior Session", command=self.navigation.load_prior_session, 
                 bg="#4169E1", fg="white").grid(row=0, column=5, padx=5, pady=2)
        
        # Previous and Next session navigation buttons
        self.a_prev_session_btn = tk.Button(session_frame, text="◀ Previous", bg="#FF8C00", fg="white",
                                         width=10, command=self.navigation.navigate_previous_session, state=tk.DISABLED)
        self.a_prev_session_btn.grid(row=0, column=6, padx=2, pady=2)
        self.a_next_session_btn = tk.Button(session_frame, text="Next ▶", bg="#FF8C00", fg="white",
                                         width=10, command=self.navigation.navigate_next_session, state=tk.DISABLED)
        self.a_next_session_btn.grid(row=0, column=7, padx=2, pady=2)
        
        # Export PDF button
        tk.Button(session_frame, text="Export PDF", bg="#9370DB", fg="white", width=12, 
                 command=self.open_export_dialog).grid(row=0, column=8, padx=2, pady=2)
        
        # Track selected sessions for navigation
        self.selected_sessions = []  # List of session numbers to navigate through
        self.selected_sessions_index = -1  # Current position in selected sessions
        
        # Row 1: Status filter radio buttons (under Edit/Delete button)
        status_filter_frame = tk.Frame(session_frame)
        status_filter_frame.grid(row=1, column=6, columnspan=4, sticky="w", padx=5, pady=5)
        
        tk.Label(status_filter_frame, text="Show Sessions:").pack(side="left", padx=(0, 10))
        tk.Radiobutton(status_filter_frame, text="Active", variable=sv.session_status_filter, 
                      value="active").pack(side="left", padx=5)
        tk.Radiobutton(status_filter_frame, text="Deleted", variable=sv.session_status_filter, 
                      value="deleted").pack(side="left", padx=5)
        tk.Radiobutton(status_filter_frame, text="Both", variable=sv.session_status_filter, 
                      value="both").pack(side="left", padx=5)
        
        # Row 2: Handler, Session Purpose
        tk.Label(session_frame, text="Handler:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        # If handler_name is set, use it; otherwise use last_handler_name
        default_handler = self.config.get("handler_name", "") or self.config.get("last_handler_name", "")
        sv.handler.set(default_handler)
        tk.Entry(session_frame, textvariable=sv.handler, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Session Purpose:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        purpose_combo = ttk.Combobox(session_frame, textvariable=sv.session_purpose, width=22,
                                     values=['Area Search Training', 'Refind Training', 
                                            'Motivational Training', 
                                            'Obedience', 'Mock Certification Test', 'Mission'])
        purpose_combo.grid(row=1, column=3, columnspan=3, sticky="w", padx=5, pady=2)
        
        # Row 3: Field Support, Dog
        tk.Label(session_frame, text="Field Support:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(session_frame, textvariable=sv.field_support, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Dog:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        # Load last dog from database (deferred until password is loaded)
        # NOTE: Commented out - will be loaded in load_initial_database_data()
        self.a_dog_combo = ttk.Combobox(session_frame, textvariable=sv.dog, width=22, state="readonly")
        # Load dogs from database (deferred)
        # NOTE: Commented out - will be loaded in load_initial_database_data()
        self.a_dog_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
        # Bind dog change to update session number
        self.a_dog_combo.bind('<<ComboboxSelected>>', self.on_dog_changed)
        
        # Search Parameters
        search_frame = tk.LabelFrame(frame, text="Search Parameters", padx=10, pady=5)
        search_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        
        tk.Label(search_frame, text="Location:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.a_location_combo = ttk.Combobox(search_frame, textvariable=sv.location, width=18, state="readonly")  # ahg added a_ 
        self.a_location_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)  # ahg added a_ 
        # Load locations from database
        self.root.after(150,self.refresh_location_list)
        
        tk.Label(search_frame, text="Search Area (Acres):").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        tk.Entry(search_frame, textvariable=sv.search_area_size, width=18).grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Number of Subjects:").grid(row=0, column=4, sticky="w", padx=5, pady=2)
        self.a_num_subjects_combo = ttk.Combobox(search_frame, textvariable=sv.num_subjects, width=15, state="readonly",
                                     values=['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
        self.a_num_subjects_combo.grid(row=0, column=5, sticky="w", padx=5, pady=2)
        self.a_num_subjects_combo.bind('<<ComboboxSelected>>', self.form_mgmt.update_subjects_found)
        
        tk.Label(search_frame, text="Handler Knowledge:").grid(row=0, column=6, sticky="w", padx=5, pady=2)
        handler_knowledge_combo = ttk.Combobox(search_frame, textvariable=sv.handler_knowledge, width=25, state="readonly",
                                              values=['Unknown number of subjects', 'Number of subjects known'])
        handler_knowledge_combo.grid(row=0, column=7, columnspan=2, sticky="w", padx=5, pady=2)
        
        # Row 1: Weather, Wind Direction, Wind Speed
        tk.Label(search_frame, text="Weather:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        weather_combo = ttk.Combobox(search_frame, textvariable=sv.weather, width=18, state="readonly",
                                     values=['Clear', 'Cloudy', 'Light Rain', 'Heavy Rain', 
                                            'Snow Cover', 'Snowing', 'Fog'])
        weather_combo.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Wind Direction:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        wind_dir_combo = ttk.Combobox(search_frame, textvariable=sv.wind_direction, width=15, state="readonly",
                                      values=['North', 'South', 'East', 'West', 
                                             'NE', 'NW', 'SE', 'SW', 'Variable'])
        wind_dir_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Wind Speed:").grid(row=1, column=4, sticky="w", padx=5, pady=2)
        tk.Entry(search_frame, textvariable=sv.wind_speed, width=18).grid(row=1, column=5, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Search Type:").grid(row=1, column=6, sticky="w", padx=5, pady=2)
        search_type_combo = ttk.Combobox(search_frame, textvariable=sv.search_type, width=25, state="readonly",
                                        values=['Single blind', 'Double blind', 'Subject coordinates known'])
        search_type_combo.grid(row=1, column=7, sticky="w", padx=5, pady=2)
        
        # Row 2: Temperature, Terrain Type
        tk.Label(search_frame, text="Temperature:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        tk.Entry(search_frame, textvariable=sv.temperature, width=21).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Add Terrain Type:").grid(row=2, column=2, sticky="w", padx=5, pady=2)
        # Load terrain types from database using DatabaseManager (respects sort_order)
        self.a_terrain_combo = ttk.Combobox(search_frame, textvariable=sv.terrain, width=15, state="readonly",
                                         values=[])
        self.a_terrain_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
        self.a_terrain_combo.bind('<<ComboboxSelected>>', self.add_to_terrain_accumulator)
        
        # Combobox for accumulated terrain types
        tk.Label(search_frame, text="Selected Terrains:").grid(row=2, column=4, sticky="w", padx=5, pady=2)
        self.a_accumulated_terrain_combo = ttk.Combobox(search_frame, textvariable=sv.accumulated_terrain, 
                                                      width=15, state="disabled", values=[])  # Start disabled
        self.a_accumulated_terrain_combo.grid(row=2, column=5, sticky="w", padx=5, pady=2)
        self.a_accumulated_terrain_combo.bind('<<ComboboxSelected>>', self.remove_terrain_from_list)
        
        # Add tooltip to accumulated terrain combobox
        from tips import ToolTip
        ToolTip(self.a_accumulated_terrain_combo, "Terrain List Accumulator\nClick an entry to remove from list", delay=750)
        
        # Track accumulated terrains as a list
        self.accumulated_terrains = []
        
        # Search Results
        results_frame = tk.LabelFrame(frame, text="Search Results", padx=10, pady=5)
        results_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        
        tk.Label(results_frame, text="Drive Level:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        drive_level_combo = ttk.Combobox(results_frame, textvariable=sv.drive_level, width=39, state="readonly",
                                        values=['High - Needed no encouragement',
                                               'Medium - Needed occasional encouragement',
                                               'Low - Needed frequent encouragement',
                                               'Would not work'])
        drive_level_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(results_frame, text="Subjects Found:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.a_subjects_found_combo = ttk.Combobox(results_frame, textvariable=sv.subjects_found, width=15, state="readonly")
        self.a_subjects_found_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        # Add tooltip that only shows when subjects_found is disabled
        ConditionalToolTip(self.a_subjects_found_combo, 
                          "Enter number of subjects found (in Search Parameters)", 
                          show_when_disabled=True)
        
        # Bind to update subject responses grid when subjects found changes
        self.a_subjects_found_combo.bind('<<ComboboxSelected>>', self.update_subject_responses_grid)
        
        # Subject Responses Treeview (row 0, columns 4-7, rowspan=2) - no LabelFrame wrapper
        # Create container with scrollbar for the treeview
        tree_container = tk.Frame(results_frame)
        tree_container.grid(row=0, column=4, columnspan=4, rowspan=2, sticky="nsew", padx=5, pady=5)
        
        # Scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_container, orient="vertical")
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview - 3 visible rows (4th row requires scrolling)
        self.a_subject_responses_tree = ttk.Treeview(
            tree_container,
            columns=('subject', 'tfr', 'refind'),
            show='headings',
            height=3,
            yscrollcommand=tree_scrollbar.set,
            selectmode='browse'
        )
        self.a_subject_responses_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.config(command=self.a_subject_responses_tree.yview)
        
        # Configure columns
        self.a_subject_responses_tree.heading('subject', text='Subject #')
        self.a_subject_responses_tree.heading('tfr', text='TFR')
        self.a_subject_responses_tree.heading('refind', text='Re-find')
        
        self.a_subject_responses_tree.column('subject', width=80, anchor='center')
        self.a_subject_responses_tree.column('tfr', width=150, anchor='w')
        self.a_subject_responses_tree.column('refind', width=150, anchor='w')
        
        # Pre-populate with 10 empty/disabled rows to support up to 10 subjects
        for i in range(1, 11):
            # Determine odd/even for alternating shading
            row_tag = 'odd' if i % 2 == 1 else 'even'
            self.a_subject_responses_tree.insert('', tk.END, iid=f'subject_{i}',
                                              values=(f'Subject {i}', '', ''),
                                              tags=(row_tag, 'disabled'))
        
        # Style for alternating rows
        self.a_subject_responses_tree.tag_configure('odd', background='#f0f0f0')  # Light gray
        self.a_subject_responses_tree.tag_configure('even', background='#ffffff')  # White
        
        # Style for enabled/disabled (text color only, preserves background)
        self.a_subject_responses_tree.tag_configure('disabled', foreground='gray')
        self.a_subject_responses_tree.tag_configure('enabled', foreground='black')
        
        # Bind single-click to edit with inline combobox
        self.a_subject_responses_tree.bind('<Button-1>', self.on_treeview_click)
        
        # Add tooltip to explain how to edit cells
        ToolTip(self.a_subject_responses_tree, 
                "Click cell under desired heading on desired row to edit value", 
                delay=750)
        
        # TFR and Re-find options for editing
        self.tfr_options = ['Strong', 'Fair', 'Required cueing', 'None']
        self.refind_options = ['Immediate', 'Required cue', 'None']
        
        # Track current editing combobox
        self.a_tree_edit_combo = None
        self.tree_edit_item = None
        self.tree_edit_column = None
        
        # Comments textbox (row 1, columns 0-3) - below Drive Level/Subjects Found, aligns with bottom of Subject Responses
        self.a_comments_text = tk.Text(results_frame, width=60, height=3, wrap=tk.WORD)
        self.a_comments_text.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=(0, 5))
        ToolTip(self.a_comments_text, "Enter comments about search here")
        
        # Maps and Images
        map_frame = tk.LabelFrame(frame, text="Maps and Images", padx=10, pady=5)
        map_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Create container for drag-drop and listbox side by side
        map_container = tk.Frame(map_frame)
        map_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - Drag and drop area
        drop_frame = tk.Frame(map_container)
        drop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.a_drop_label = tk.Label(
            drop_frame,
            text="Drag & Drop Maps/Images\n(PDF/JPG/PNG)",
            bg="#e0e0e0",
            relief="ridge",
            height=4
        )
        self.a_drop_label.pack(fill=tk.BOTH, expand=True)
        
        # Enable drag and drop
        self.a_drop_label.drop_target_register(DND_FILES)
        self.a_drop_label.dnd_bind('<<Drop>>', self.file_ops.handle_drop)
        self.a_drop_label.dnd_bind('<<DragEnter>>', self.file_ops.drag_enter)
        self.a_drop_label.dnd_bind('<<DragLeave>>', self.file_ops.drag_leave)
        
        # Right side - Listbox with scrollbar and view button
        list_frame = tk.Frame(map_container)
        list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Container for listbox and buttons on same row
        list_button_container = tk.Frame(list_frame)
        list_button_container.pack(fill=tk.BOTH, expand=True)
        
        listbox_container = tk.Frame(list_button_container)
        listbox_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.a_map_listbox = tk.Listbox(listbox_container, height=3, font=('Arial', 9))
        map_scroll = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL,
                                   command=self.a_map_listbox.yview)
        self.a_map_listbox.config(yscrollcommand=map_scroll.set)
        
        self.a_map_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        map_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to open file
        self.a_map_listbox.bind('<Double-Button-1>', lambda e: self.file_ops.view_selected_map())
        
        # Button frame to the right of listbox
        map_button_frame = tk.Frame(list_button_container)
        map_button_frame.pack(side=tk.RIGHT, padx=(5, 0))
        
        # View button
        self.a_view_map_button = tk.Button(map_button_frame, text="View Selected", 
                                         command=self.file_ops.view_selected_map, state=tk.DISABLED, width=12)
        self.a_view_map_button.pack(pady=(0, 2))
        
        # Delete button
        self.a_delete_map_button = tk.Button(map_button_frame, text="Delete Selected", 
                                         command=self.file_ops.delete_selected_map, state=tk.DISABLED, width=12)
        self.a_delete_map_button.pack(pady=(2, 0))
        
        self.map_files_list = []  # Store list of files
        
        # Bottom buttons
        button_frame = tk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=20)
        
        tk.Button(button_frame, text="Save Session", command=self.save_session,
                 bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"),
                 width=25, height=2).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Clear Form", command=self.form_mgmt.clear_form,
                 width=15).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Quit", command=self.root.quit,
                 width=10).pack(side="left", padx=10)
        
        # Initialize navigation button states
        self.root.after(500, self.navigation.update_navigation_buttons)
        
        # Initialize subjects_found as disabled (no subjects selected yet)
        self.a_subjects_found_combo['state'] = 'disabled'
    
    # Placeholder methods for Entry tab buttons
    def initialize_entry_tab_data(self):
        """Load all database data for Entry tab - called after password is loaded"""
        from sv import sv
        
        # last_dog = DatabaseOperations(self).load_db_setting("last_dog_name", "")
        # self.refresh_dog_list()
        db_mgr = get_db_manager(sv.db_type.get())
        terrain_types = db_mgr.load_terrain_types()
        # Update terrain combobox with loaded data
        if hasattr(self, 'terrain_combo'):
            self.a_terrain_combo['values'] = terrain_types


    def add_to_terrain_accumulator(self, event=None):
        """Add selected terrain type to the accumulated terrains list"""
        terrain_type = sv.terrain.get()
        if terrain_type:
            # Check for duplicates
            if terrain_type in self.accumulated_terrains:
                messagebox.showinfo("Duplicate", f"'{terrain_type}' is already in the list")
                sv.terrain.set("")
                return
            
            # Add to list
            self.accumulated_terrains.append(terrain_type)
            
            # Update combobox values
            self.a_accumulated_terrain_combo['values'] = self.accumulated_terrains
            
            # Enable the combobox if this is the first item
            if len(self.accumulated_terrains) == 1:
                self.a_accumulated_terrain_combo['state'] = 'readonly'
            
            # Display the last (newest) entry
            sv.accumulated_terrain.set(terrain_type)
            
            # Clear selection in add terrain combobox
            sv.terrain.set("")
    
    def remove_terrain_from_list(self, event):
        """Remove terrain type from list when clicked/selected"""
        terrain_type = sv.accumulated_terrain.get()
        if not terrain_type:
            return
        
        # Confirm removal
        if messagebox.askyesno("Remove Terrain Type", 
                              f"Remove '{terrain_type}' from the list?"):
            # Find the index of the item being removed
            removed_index = self.accumulated_terrains.index(terrain_type)
            
            # Remove from list
            self.accumulated_terrains.remove(terrain_type)
            
            # Update combobox values
            self.a_accumulated_terrain_combo['values'] = self.accumulated_terrains
            
            # Determine what to display after removal
            if len(self.accumulated_terrains) == 0:
                # List is now empty - show blank and disable combobox
                sv.accumulated_terrain.set("")
                self.a_accumulated_terrain_combo['state'] = 'disabled'
            elif removed_index < len(self.accumulated_terrains):
                # Show the item that's now at the same index (the one that was below)
                sv.accumulated_terrain.set(self.accumulated_terrains[removed_index])
            else:
                # The last item was removed - show the new last item
                sv.accumulated_terrain.set(self.accumulated_terrains[-1])
    
    def update_subject_responses_grid(self, event=None):
        """Update subject responses grid - enable/disable rows based on Subjects Found value"""
        subjects_found = sv.subjects_found.get()
        
        # Parse subjects found value (e.g., "2 out of 3" -> 2 found)
        num_found = 0
        if subjects_found and " out of " in subjects_found:
            try:
                num_found = int(subjects_found.split(" out of ")[0])
            except:
                pass
        
        # Update tags on all 10 rows - enable those within num_found, disable others
        for i in range(1, 11):
            item_id = f'subject_{i}'
            # Determine odd/even tag for this row
            row_tag = 'odd' if i % 2 == 1 else 'even'
            
            if i <= num_found:
                # Enable this row (keep odd/even tag for background shading)
                self.a_subject_responses_tree.item(item_id, tags=(row_tag, 'enabled'))
            else:
                # Disable this row and clear values (keep odd/even tag for background shading)
                self.a_subject_responses_tree.item(item_id, values=(f'Subject {i}', '', ''), tags=(row_tag, 'disabled'))
    
    def on_treeview_click(self, event):
        """Handle click on treeview - show inline combobox for TFR/Re-find columns"""
        # Identify what was clicked
        region = self.a_subject_responses_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        
        item = self.a_subject_responses_tree.identify_row(event.y)
        column = self.a_subject_responses_tree.identify_column(event.x)
        
        if not item or not column:
            return
        
        # Check if row is enabled
        tags = self.a_subject_responses_tree.item(item, 'tags')
        if 'disabled' in tags:
            return  # Don't allow editing disabled rows
        
        # Determine which column was clicked (column is like '#1', '#2', '#3')
        col_index = int(column.replace('#', ''))
        
        # Only allow editing TFR (column 2) and Re-find (column 3)
        if col_index not in [2, 3]:
            return
        
        # Close any existing edit combobox
        self.close_tree_edit()
        
        # Get the bounding box of the cell
        x, y, width, height = self.a_subject_responses_tree.bbox(item, column)
        
        # Get current values
        values = list(self.a_subject_responses_tree.item(item, 'values'))
        current_value = values[col_index - 1] if col_index <= len(values) else ''
        
        # Determine options based on column
        if col_index == 2:  # TFR column
            options = self.tfr_options
        else:  # Re-find column
            options = self.refind_options
        
        # Create combobox positioned over the cell
        self.a_tree_edit_combo = ttk.Combobox(
            self.a_subject_responses_tree,
            values=options,
            state='readonly'
        )
        self.a_tree_edit_combo.set(current_value)
        
        # Position the combobox
        self.a_tree_edit_combo.place(x=x, y=y, width=width, height=height)
        
        # Store editing context
        self.tree_edit_item = item
        self.tree_edit_column = col_index
        
        # Bind events
        self.a_tree_edit_combo.bind('<<ComboboxSelected>>', self.on_tree_edit_select)
        self.a_tree_edit_combo.bind('<FocusOut>', lambda e: self.close_tree_edit())
        self.a_tree_edit_combo.bind('<Escape>', lambda e: self.close_tree_edit())
        
        # Focus and open dropdown
        self.a_tree_edit_combo.focus_set()
        self.a_tree_edit_combo.event_generate('<Button-1>')
    
    def on_tree_edit_select(self, event=None):
        """Handle selection in inline edit combobox"""
        if not self.a_tree_edit_combo or not self.tree_edit_item:
            return
        
        # Get the new value
        new_value = self.a_tree_edit_combo.get()
        
        # Update the treeview
        values = list(self.a_subject_responses_tree.item(self.tree_edit_item, 'values'))
        values[self.tree_edit_column - 1] = new_value
        self.a_subject_responses_tree.item(self.tree_edit_item, values=values)
        
        # Close the combobox
        self.close_tree_edit()
    
    def close_tree_edit(self):
        """Close the inline edit combobox"""
        if self.a_tree_edit_combo:
            self.a_tree_edit_combo.destroy()
            self.a_tree_edit_combo = None
        self.tree_edit_item = None
        self.tree_edit_column = None
    
    def reset_subject_responses_tree_selection(self):
        """Reset tree selection and scroll to subject 1"""
        if hasattr(self, 'subject_responses_tree'):
            # Clear any current selection
            self.a_subject_responses_tree.selection_remove(self.a_subject_responses_tree.selection())
            
            # Select subject 1 (first item)
            first_item = 'subject_1'
            if self.a_subject_responses_tree.exists(first_item):
                self.a_subject_responses_tree.selection_set(first_item)
                self.a_subject_responses_tree.see(first_item)  # Scroll to make it visible
    
    def open_export_dialog(self):
        """Open export PDF dialog"""
        # Check if dog is selected
        if not sv.dog.get():
            messagebox.showwarning("No Dog Selected", "Please select a dog before exporting")
            return
        
        # Check if trail maps folder is configured
        trail_maps_folder = sv.trail_maps_folder.get().strip()
        if not trail_maps_folder:
            messagebox.showwarning("Trail Maps Folder Not Set", 
                                 "Trail maps folder not configured.\n\n"
                                 "Images will not be included in the PDF.\n\n"
                                 "Configure in Setup tab to include images.")
        
        # Import the export module
        import export_pdf
        
        # Get database connection function
        def get_connection():
            import config
            from database import engine
            return engine.connect()
        
        # Show export dialog
        export_pdf.show_export_dialog(
            parent=self.root,
            db_type=sv.db_type.get(),
            current_dog=sv.dog.get(),
            get_connection_func=get_connection,
            backup_folder=sv.backup_folder.get().strip(),
            trail_maps_folder=trail_maps_folder
        )
    
    # File/Folder selection methods
    def update_create_db_button_state(self, *args):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.update_create_db_button_state()

    def add_entry_context_menu(self, entry_widget):
        """Delegate to SetupTab module"""
        return self.setup_tab_mgr.add_entry_context_menu(entry_widget)
    
    def entry_cut(self, entry_widget):
        """Cut selected text from Entry widget"""
        try:
            entry_widget.event_generate("<<Cut>>")
        except:
            pass
    
    def entry_copy(self, entry_widget):
        """Copy selected text from Entry widget"""
        try:
            entry_widget.event_generate("<<Copy>>")
        except:
            pass
    
    def entry_paste(self, entry_widget):
        """Paste text into Entry widget"""
        try:
            entry_widget.event_generate("<<Paste>>")
        except:
            pass
    
    def entry_select_all(self, entry_widget):
        """Select all text in Entry widget"""
        try:
            entry_widget.select_range(0, tk.END)
            entry_widget.icursor(tk.END)
        except:
            pass
    

    def set_db_password(self):
        """Set database password in config at runtime and optionally save encrypted"""
        import config
        
        db_type = sv.db_type.get()
        password = sv.db_password.get()
        
        if db_type in ["postgres", "supabase", "mysql"] and password:
            # Set the password in config
            config.DB_PASSWORD = password
            
            # Build the connection URL with password
            url_template = config.DB_CONFIG[db_type].get("url_template", "")
            if url_template:
                config.DB_CONFIG[db_type]["url"] = url_template.format(password=password)
            
            # CRITICAL: Dispose any existing database engines to force reconnection
            # This ensures the new password is used
            try:
                from ui_database import dispose_all_engines
                dispose_all_engines()
            except:
                pass  # If ui_database doesn't have this function, skip
            
            # Save encrypted password if "Remember" is checked
            # Check if remember_password_var exists (may not during initialization)
            if hasattr(self, 'remember_password_var') and sv.remember_password.get():
                from password_manager import save_encrypted_password, check_crypto_available
                
                if check_crypto_available():
                    if save_encrypted_password(self.config, db_type, password):
                        self.save_config()
                        # Update status (sv.status is always available from sv module)
                        sv.status.set(f"Password saved (encrypted) for {db_type}")
                    else:
                        messagebox.showwarning(
                            "Encryption Failed",
                            "Could not encrypt password. It will not be saved."
                        )
                else:
                    messagebox.showwarning(
                        "Cryptography Not Available",
                        "Password encryption requires the 'cryptography' library.\n\n"
                        "Install with: pip install cryptography\n\n"
                        "Password will not be saved."
                    )
    
    def forget_password(self):
        """Delegate to SetupTab module"""
        return self.setup_tab_mgr.forget_password()
    
    def prepare_db_connection(self, db_type):
        """Prepare database connection by setting password if needed"""
        if db_type in ["postgres", "supabase", "mysql"]:
            password = sv.db_password.get().strip()
            if not password:
                messagebox.showerror(
                    "Password Required",
                    f"Please enter the database password for {db_type} in the Setup tab."
                )
                return False
            
            # Update the password
            sv.db_password.set(password)
            self.set_db_password()
        
        return True
    
    def create_database(self):
        """Delegate to Setup tab manager"""
        return self.setup_tab_mgr.create_database()

    def load_locations_from_database(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.load_locations_from_database()

    def refresh_location_list(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.refresh_location_list()

    def refresh_terrain_list(self):
        """Refresh the terrain type combobox in Entry tab"""
        # Ensure database is ready (critical for networked databases)
        self.misc_data_ops.ensure_db_ready()
        
        # Use DatabaseManager to get terrain types in correct order (by sort_order)
        from ui_database import get_db_manager
        db_mgr = get_db_manager(sv.db_type.get())
        terrain_types = db_mgr.load_terrain_types()
        
        # Update combobox
        if hasattr(self, 'terrain_combo'):
            self.a_terrain_combo['values'] = terrain_types
    
    def load_terrain_from_database(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.load_terrain_from_database()

    def load_distraction_from_database(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.load_distraction_from_database()

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

    def load_dogs_from_database(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.load_dogs_from_database()

    def refresh_dog_list(self):
        """Delegate to Setup tab manager"""
        self.setup_tab_mgr.refresh_dog_list()

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

    def on_closing(self):
        """Handle window close event"""
        if self.form_mgmt.check_unsaved_changes("exit"):
            self.root.destroy()
    
    def on_tab_changed(self, event):
        """Handle tab change event - check for setup requirements and unsaved changes"""
        current_tab_index = self.notebook.index(self.notebook.select())
        
        # Check if we're leaving the Setup tab (index 0)
        if self.previous_tab_index == 0 and current_tab_index != 0:
            # First, check if database and folders are configured
            if not self.check_setup_requirements():
                # Requirements not met - stay on Setup tab
                self.notebook.select(self.setup_tab)
                self.previous_tab_index = 0
                return
            
            # Then check for unsaved changes
            if not self.form_mgmt.check_unsaved_changes("switch tabs"):
                # User cancelled - switch back to Setup tab
                self.notebook.select(self.setup_tab)
                self.previous_tab_index = 0
                return
            
            # CRITICAL: Ensure password is set for networked databases before switching tabs
            # This prevents authentication errors when Session tab tries to connect
            db_type = sv.db_type.get()
            if db_type in ["postgres", "supabase", "mysql"]:
                # Make sure password is set in database config
                password = sv.db_password.get().strip()
                if password:
                    self.set_db_password()
                
                # Show working dialog when switching to Training Session tab
                # This gives time for UI to load and become responsive
                working_dialog = WorkingDialog(self.root, "Loading Session", 
                                             f"Loading Training Session tab...")
                self.root.update()
                
                # Small delay to ensure UI is ready
                self.root.after(300, lambda: working_dialog.close(delay_ms=200))
            
        # Update previous tab index
        self.previous_tab_index = current_tab_index
    
    def check_setup_requirements(self):
        """Check if database and required folders are configured before leaving Setup tab"""
        db_type = sv.db_type.get()
        
        # For SQLite, check if database file exists BEFORE trying to connect
        if db_type == "sqlite":
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            if not os.path.exists(db_path):
                # Database file doesn't exist
                database_exists = False
            else:
                # File exists - check if tables exist
                try:
                    import config
                    old_db_type = config.DB_TYPE
                    config.DB_TYPE = db_type
                    
                    from database import engine
                    engine.dispose()
                    from importlib import reload
                    import database
                    reload(database)
                    
                    from sqlalchemy import text
                    
                    # Try to query the dogs table
                    with database.get_connection() as conn:
                        conn.execute(text("SELECT COUNT(*) FROM dogs"))
                    
                    # Restore original DB_TYPE
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                    
                    database_exists = True
                    
                except Exception as e:
                    # Restore original DB_TYPE on error
                    try:
                        import config
                        import database
                        from importlib import reload
                        config.DB_TYPE = old_db_type
                        database.engine.dispose()
                        reload(database)
                    except:
                        pass
                    
                    if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                        database_exists = False
                    else:
                        # Some other error - allow switching but log it
                        print(f"Error checking database: {e}")
                        database_exists = True
        else:
            # For PostgreSQL/Supabase, try to connect and query
            try:
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Try to query the dogs table
                with database.get_connection() as conn:
                    conn.execute(text("SELECT COUNT(*) FROM dogs"))
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                database_exists = True
                
            except Exception as e:
                # Restore original DB_TYPE on error
                try:
                    import config
                    import database
                    from importlib import reload
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except:
                    pass
                
                if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                    database_exists = False
                else:
                    # Some other error - allow switching but log it
                    print(f"Error checking database: {e}")
                    database_exists = True
        
        # Check required folders - get directly from sv
        backup_folder = sv.backup_folder.get().strip()
        trail_maps_folder = sv.trail_maps_folder.get().strip()
        
        # DEBUG - show what we found
        # print(f"DEBUG check_setup_requirements:")
        print(f"  backup_folder = '{backup_folder}'")
        print(f"  trail_maps_folder = '{trail_maps_folder}'")
        print(f"  backup exists on disk: {os.path.exists(backup_folder) if backup_folder else False}")
        print(f"  trail_maps exists on disk: {os.path.exists(trail_maps_folder) if trail_maps_folder else False}")
        
        # Build error messages
        errors = []
        if not database_exists:
            errors.append("• Database not created")
        
        # Check both that folder is set AND exists on disk
        if not backup_folder or not os.path.exists(backup_folder):
            if not backup_folder:
                errors.append("• Backup folder not selected")
            else:
                errors.append(f"• Backup folder does not exist: {backup_folder}")
        
        if not trail_maps_folder or not os.path.exists(trail_maps_folder):
            if not trail_maps_folder:
                errors.append("• Trail Maps Storage folder not selected")
            else:
                errors.append(f"• Trail Maps Storage folder does not exist: {trail_maps_folder}")
        
        # If there are errors, show message and prevent switching
        if errors:
            error_msg = "Setup Required\n\n"
            error_msg += "Before using the Entry tab, please complete:\n\n"
            error_msg += "\n".join(errors)
            error_msg += "\n\nPlease complete the setup on the Setup tab."
            
            messagebox.showwarning("Setup Required", error_msg)
            return False
        
        return True
    
    def add_entry_context_menu(self, entry_widget):
        """Add right-click context menu to Entry widget with Cut/Copy/Paste/Select All"""
        context_menu = tk.Menu(entry_widget, tearoff=0)
        
        context_menu.add_command(label="Cut", command=lambda: self.entry_cut(entry_widget))
        context_menu.add_command(label="Copy", command=lambda: self.entry_copy(entry_widget))
        context_menu.add_command(label="Paste", command=lambda: self.entry_paste(entry_widget))
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=lambda: self.entry_select_all(entry_widget))
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        # Bind right-click (Button-3 on Linux/Windows, Button-2 on Mac)
        entry_widget.bind("<Button-3>", show_context_menu)
        # Also bind Control-Button-1 for Mac users
        entry_widget.bind("<Control-Button-1>", show_context_menu)
    
    def entry_cut(self, entry_widget):
        """Cut selected text from Entry widget"""
        try:
            entry_widget.event_generate("<<Cut>>")
        except:
            pass
    
    def entry_copy(self, entry_widget):
        """Copy selected text from Entry widget"""
        try:
            entry_widget.event_generate("<<Copy>>")
        except:
            pass
    
    def entry_paste(self, entry_widget):
        """Paste text into Entry widget"""
        try:
            entry_widget.event_generate("<<Paste>>")
        except:
            pass
    
    def entry_select_all(self, entry_widget):
        """Select all text in Entry widget"""
        try:
            entry_widget.select_range(0, tk.END)
            entry_widget.icursor(tk.END)
        except:
            pass
    
    def on_db_type_changed(self):
        """Show/hide password field based on database type and load saved password"""
        import sv
        db_type = sv.db_type.get()
        
        # Show password field for postgres, supabase, mysql
        # Hide for sqlite
        if db_type in ["postgres", "supabase", "mysql"]:
            if hasattr(self.setup_tab_mgr, 's_db_password_frame'):
                self.setup_tab_mgr.s_db_password_frame.pack(pady=5)
            
            # Try to load saved encrypted password for this database type
            from password_manager import get_decrypted_password, check_crypto_available
            
            if check_crypto_available():
                saved_password = get_decrypted_password(self.config, db_type)
                if saved_password:
                    sv.db_password.set(saved_password)
                    # CRITICAL FIX: Actually set the password in the database configuration
                    # Without this, the password shows in the field but isn't used for connection
                    self.set_db_password()
                    # Only update status if status_var exists (may not during initialization)
                    if hasattr(sv, 'status'):
                        sv.status.set(f"Loaded saved password for {db_type}")
                else:
                    sv.db_password.set("")
            else:
                sv.db_password.set("")
        else:
            if hasattr(self.setup_tab_mgr, 's_db_password_frame'):
                self.setup_tab_mgr.s_db_password_frame.pack_forget()
        
        # Force UI update to keep splash countdown animating
        if hasattr(self, 'root'):
            try:
                self.root.update_idletasks()
            except:
                pass
    
    def toggle_password_visibility(self):
        """Toggle password visibility in entry field"""
        import sv
        if sv.show_password.get():
            if hasattr(self.setup_tab, 's_db_password_entry'):
                self.setup_tab.s_db_password_entry.config(show="")
        else:
            if hasattr(self.setup_tab, 's_db_password_entry'):
                self.setup_tab.s_db_password_entry.config(show="*")
    
    def set_db_password(self):
        """Set database password in config at runtime and optionally save encrypted"""
        import config
        import sv
        
        db_type = sv.db_type.get()
        password = sv.db_password.get()
        
        if db_type in ["postgres", "supabase", "mysql"] and password:
            # Set the password in config
            config.DB_PASSWORD = password
            
            # Build the connection URL with password
            url_template = config.DB_CONFIG[db_type].get("url_template", "")
            if url_template:
                config.DB_CONFIG[db_type]["url"] = url_template.format(password=password)
            
            # CRITICAL: Dispose any existing database engines to force reconnection
            # This ensures the new password is used
            try:
                from ui_database import dispose_all_engines
                dispose_all_engines()
            except:
                pass  # If ui_database doesn't have this function, skip
            
            # Save encrypted password if "Remember" is checked
            if sv.remember_password.get():
                from password_manager import save_encrypted_password, check_crypto_available
                
                if check_crypto_available():
                    if save_encrypted_password(self.config, db_type, password):
                        self.save_config()
                        # Only update status if status_var exists (may not during initialization)
                        if hasattr(sv, 'status'):
                            sv.status.set(f"Password saved (encrypted) for {db_type}")
                    else:
                        messagebox.showwarning(
                            "Encryption Failed",
                            "Could not encrypt password. It will not be saved."
                        )
                else:
                    messagebox.showwarning(
                        "Cryptography Not Available",
                        "Password encryption requires the 'cryptography' library.\n\n"
                        "Install with: pip install cryptography\n\n"
                        "Password will not be saved."
                    )
    
    def forget_password(self):
        """Clear saved encrypted password for current database type"""
        import sv
        db_type = sv.db_type.get()
        
        if db_type not in ["postgres", "supabase", "mysql"]:
            return
        
        from password_manager import clear_saved_password
        
        # Clear from config
        clear_saved_password(self.config, db_type)
        self.save_config()
        
        # Clear from UI
        sv.db_password.set("")
        
        sv.status.set(f"Forgot saved password for {db_type}")
        messagebox.showinfo("Password Cleared", f"Saved password for {db_type} has been cleared.")
    
    def prepare_db_connection(self, db_type):
        """Prepare database connection by setting password if needed"""
        import sv
        if db_type in ["postgres", "supabase", "mysql"]:
            password = sv.db_password.get().strip()
            if not password:
                messagebox.showerror(
                    "Password Required",
                    f"Please enter the database password for {db_type} in the Setup tab."
                )
                return False
            
            # Set the password before any database operations
            self.set_db_password()
        
        return True
    
    def run(self):
        """Start the application"""
        self.root.mainloop()
