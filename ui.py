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
from about_dialog import show_about
from tips import ToolTip, ConditionalToolTip
from ui_utils import get_username, get_default_terrain_types, get_default_distraction_types
from ui_database import get_db_manager
from working_dialog import WorkingDialog, run_with_working_dialog

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
        self.db_path_var = tk.StringVar(value=self.machine_db_path)
        self.folder_path_var = tk.StringVar(value=self.machine_trail_maps_folder)
        self.backup_path_var = tk.StringVar(value=self.machine_backup_folder)
        self.config_path_var = tk.StringVar(value=str(self.config_file))
        
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
        self.select_initial_tab()
        
        # Status bar at bottom (create before using it below)
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                            bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Schedule session number update AFTER password is loaded (happens at 100ms)
        # This prevents database calls before authentication is ready
        def update_initial_session():
            loaded_dog = self.dog_var.get()
            if loaded_dog:
                next_session = self.get_next_session_number(loaded_dog)
                self.session_var.set(str(next_session))
                self.status_var.set(f"Ready - {loaded_dog} - Next session: #{next_session}")
                # Update navigation button states
                self.update_navigation_buttons()
        
        # Delay until after password is loaded (300ms > 100ms for on_db_type_changed)
        self.root.after(300, update_initial_session)
        
        # Track form state for unsaved changes detection
        self.form_snapshot = ""
        
        # Show main window (splash will be on top due to topmost attribute)
        self.root.deiconify()
        
        # Take initial snapshot after UI is ready
        self.root.after(100, self.take_form_snapshot)
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    
    def select_initial_tab(self):
        """Select initial tab based on database existence"""
        db_type = self.db_type_var.get()
        database_exists = False
        
        # Check if database exists
        if db_type == "sqlite":
            # For SQLite, check if database file exists
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            if os.path.exists(db_path):
                # Check if it has tables (not just an empty file)
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
                    
                    # Try to query a table
                    with database.get_connection() as conn:
                        conn.execute(text("SELECT COUNT(*) FROM training_sessions"))
                    
                    database_exists = True
                    
                    # Restore original DB_TYPE
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except:
                    # If query fails, database doesn't have proper tables
                    try:
                        import config
                        import database
                        from importlib import reload
                        config.DB_TYPE = old_db_type
                        database.engine.dispose()
                        reload(database)
                    except:
                        pass
                    database_exists = False
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
                
                # Try to query a table
                with database.get_connection() as conn:
                    conn.execute(text("SELECT COUNT(*) FROM training_sessions"))
                
                database_exists = True
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                # If connection or query fails, database doesn't exist
                try:
                    import config
                    import database
                    from importlib import reload
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except:
                    pass
                database_exists = False
        
        # Select appropriate tab
        if database_exists:
            # Database exists - show Training Session Entry tab
            self.notebook.select(self.entry_tab)
            self.previous_tab_index = 1  # Update to reflect we're on Entry tab
        else:
            # No database - show Setup tab (already default)
            self.notebook.select(self.setup_tab)
            self.previous_tab_index = 0
    
    def save_session_to_json(self, session_data):
        """Save session data to JSON backup file"""
        backup_folder = self.backup_path_var.get().strip()
        if not backup_folder:
            # No backup folder configured, skip
            return
        
        from pathlib import Path
        backup_path = Path(backup_folder)
        if not backup_path.exists():
            print(f"Warning: Backup folder does not exist: {backup_folder}")
            return
        
        # Create filename: <dogname>_session_<number>_<date>.json
        session_num = session_data.get('session_number')
        date_str = session_data.get('date', '').replace('-', '')
        dog_name = session_data.get('dog_name', 'unknown')
        
        # Sanitize dog name for filename (remove special characters)
        import re
        safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
        
        filename = f"{safe_dog_name}_session_{session_num}_{date_str}.json"
        filepath = backup_path / filename
        
        try:
            # Add timestamp
            session_data['backup_timestamp'] = datetime.now().isoformat()
            
            # Write JSON file
            with open(filepath, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            print(f"Session backup saved: {filepath}")
        except Exception as e:
            print(f"Warning: Failed to save session backup: {e}")
    
    def save_settings_backup(self):
        """Save settings to JSON backup file"""
        backup_folder = self.backup_path_var.get().strip()
        if not backup_folder:
            # No backup folder configured, skip
            return
        
        from pathlib import Path
        backup_path = Path(backup_folder)
        if not backup_path.exists():
            print(f"Warning: Backup folder does not exist: {backup_folder}")
            return
        
        try:
            db_type = self.db_type_var.get()
            
            # Collect dogs from database
            dogs = []
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
                
                # Check if database file exists
                if db_type == "sqlite":
                    import config as config_module
                    db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
                    if os.path.exists(db_path):
                        with database.get_connection() as conn:
                            result = conn.execute(text("SELECT name FROM dogs ORDER BY name"))
                            dogs = [row[0] for row in result]
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                pass  # If database doesn't exist yet, dogs list stays empty
            
            # Collect locations from database
            locations = []
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
                
                # Check if database file exists
                if db_type == "sqlite":
                    import config as config_module
                    db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
                    if os.path.exists(db_path):
                        with database.get_connection() as conn:
                            result = conn.execute(text("SELECT name FROM training_locations ORDER BY name"))
                            locations = [row[0] for row in result]
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                pass  # If database doesn't exist yet, locations list stays empty
            
            # Collect terrain types from database
            terrain_types = []
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
                
                # Check if database file exists
                if db_type == "sqlite":
                    import config as config_module
                    db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
                    if os.path.exists(db_path):
                        with database.get_connection() as conn:
                            result = conn.execute(text("SELECT name FROM terrain_types ORDER BY name"))
                            terrain_types = [row[0] for row in result]
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                pass  # If database doesn't exist yet, terrain_types list stays empty
            
            # Collect distraction types from database
            distraction_types = []
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
                
                # Check if database file exists
                if db_type == "sqlite":
                    import config as config_module
                    db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
                    if os.path.exists(db_path):
                        with database.get_connection() as conn:
                            result = conn.execute(text("SELECT name FROM distraction_types ORDER BY name"))
                            distraction_types = [row[0] for row in result]
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                pass  # If database doesn't exist yet, distraction_types list stays empty
            
            # Get handler name from config
            handler_name = self.config.get("handler_name", "")
            
            # Create settings dictionary
            settings = {
                "dogs": sorted(dogs),
                "training_locations": sorted(locations),
                "terrain_types": sorted(terrain_types),
                "distraction_types": sorted(distraction_types),
                "handler_name": handler_name,
                "backup_date": datetime.now().isoformat()
            }
            
            # Save to file
            settings_path = backup_path / "airscenting_settings.json"
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
            
            print(f"Settings backup saved: {settings_path}")
            
        except Exception as e:
            print(f"Warning: Failed to save settings backup: {e}")
    
    def restore_settings_from_json(self):
        """Restore settings from JSON backup file"""
        backup_folder = self.backup_path_var.get().strip()
        if not backup_folder:
            messagebox.showwarning("No Backup Folder", "Please select a backup folder first")
            return
        
        from pathlib import Path
        backup_path = Path(backup_folder)
        if not backup_path.exists():
            messagebox.showwarning("Invalid Folder", f"Backup folder does not exist:\n{backup_folder}")
            return
        
        settings_path = backup_path / "airscenting_settings.json"
        if not settings_path.exists():
            messagebox.showinfo("No Settings Backup", 
                               f"No settings backup file found in:\n{backup_folder}\n\n"
                               f"Looking for: airscenting_settings.json")
            return
        
        try:
            # Load settings
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            
            db_type = self.db_type_var.get()
            
            # Insert dogs to database
            dogs = settings.get("dogs", [])
            dogs_added = 0
            
            if dogs:
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
                    
                    for dog_name in dogs:
                        try:
                            with database.get_connection() as conn:
                                conn.execute(
                                    text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": dog_name, "user_name": get_username()}
                                )
                                conn.commit()
                            dogs_added += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e) and "duplicate key" not in str(e):
                                print(f"Failed to add dog '{dog_name}': {e}")
                    
                    # Restore original DB_TYPE
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except Exception as e:
                    print(f"Error restoring dogs: {e}")
            
            # Insert locations to database
            locations = settings.get("training_locations", [])
            locations_added = 0
            
            if locations:
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
                    
                    for location in locations:
                        try:
                            with database.get_connection() as conn:
                                conn.execute(
                                    text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": location, "user_name": get_username()}
                                )
                                conn.commit()
                            locations_added += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e) and "duplicate key" not in str(e):
                                print(f"Failed to add location '{location}': {e}")
                    
                    # Restore original DB_TYPE
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except Exception as e:
                    print(f"Error restoring locations: {e}")
            
            # Insert terrain types to database
            terrain_types = settings.get("terrain_types", [])
            terrain_added = 0
            
            if terrain_types:
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
                    
                    for terrain in terrain_types:
                        try:
                            with database.get_connection() as conn:
                                conn.execute(
                                    text("INSERT INTO terrain_types (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": terrain, "user_name": get_username()}
                                )
                                conn.commit()
                            terrain_added += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e) and "duplicate key" not in str(e):
                                print(f"Failed to add terrain type '{terrain}': {e}")
                    
                    # Restore original DB_TYPE
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except Exception as e:
                    print(f"Error restoring terrain types: {e}")
            
            # Insert distraction types to database
            distraction_types = settings.get("distraction_types", [])
            distraction_added = 0
            
            if distraction_types:
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
                    
                    for distraction in distraction_types:
                        try:
                            with database.get_connection() as conn:
                                conn.execute(
                                    text("INSERT INTO distraction_types (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": distraction, "user_name": get_username()}
                                )
                                conn.commit()
                            distraction_added += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e) and "duplicate key" not in str(e):
                                print(f"Failed to add distraction type '{distraction}': {e}")
                    
                    # Restore original DB_TYPE
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except Exception as e:
                    print(f"Error restoring distraction types: {e}")
            
            # Save handler name to config
            if "handler_name" in settings:
                self.config["handler_name"] = settings["handler_name"]
                self.default_handler_var.set(settings["handler_name"])
            
            self.save_config()
            
            # Refresh UI
            self.load_dogs_from_database()
            if hasattr(self, 'dog_combo'):
                self.refresh_dog_list()
            
            self.load_locations_from_database()
            if hasattr(self, 'location_combo'):
                self.refresh_location_list()
            
            # Reload terrain and distraction lists from database
            self.load_terrain_from_database()
            self.load_distraction_from_database()
            # Also refresh Entry tab terrain combobox
            if hasattr(self, 'terrain_combo'):
                self.refresh_terrain_list()
            
            # Show summary
            msg = "Settings restored successfully!\n\n"
            if dogs_added > 0:
                msg += f"Added {dogs_added} dog(s)\n"
            if locations_added > 0:
                msg += f"Added {locations_added} location(s)\n"
            if terrain_added > 0:
                msg += f"Added {terrain_added} terrain type(s)\n"
            if distraction_added > 0:
                msg += f"Added {distraction_added} distraction type(s)\n"
            if "handler_name" in settings:
                msg += f"Restored handler name: {settings['handler_name']}\n"
            
            messagebox.showinfo("Restore Complete", msg)
            
        except Exception as e:
            messagebox.showerror("Restore Error", f"Failed to restore settings:\n{e}")
            print(f"Error restoring settings: {e}")
    
    def restore_from_json_backups(self, db_type):
        """Restore database from JSON backup files"""
        backup_folder = self.backup_path_var.get().strip()
        if not backup_folder:
            messagebox.showwarning("No Backup Folder", "No backup folder configured")
            return False
        
        from pathlib import Path
        backup_path = Path(backup_folder)
        if not backup_path.exists():
            messagebox.showwarning("Invalid Folder", f"Backup folder does not exist:\n{backup_folder}")
            return False
        
        # Find all session JSON files (both old and new format)
        # Old format: session_<number>_<date>.json
        # New format: <dogname>_session_<number>_<date>.json
        json_files = list(backup_path.glob("*session_*.json"))
        if not json_files:
            messagebox.showinfo("No Backups Found", 
                               f"No session backup files found in:\n{backup_folder}")
            return False
        
        # Ask user to confirm restore
        result = messagebox.askyesno(
            "Restore from Backups",
            f"Found {len(json_files)} session backup files.\n\n"
            f"Do you want to restore these sessions to the new database?",
            icon='question'
        )
        
        if not result:
            return False
        
        # Restore sessions
        # Show working dialog for networked databases
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.root, "Restoring", 
                                         f"Restoring {len(json_files)} sessions to {db_type} database...")
            self.root.update()
        else:
            working_dialog = None
        
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
            
            restored_count = 0
            failed_count = 0
            dog_names = set()  # Collect unique dog names
            location_names = set()  # Collect unique location names
            
            for json_file in sorted(json_files):
                try:
                    with open(json_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Collect dog name for later insertion
                    dog_name = session_data.get('dog_name')
                    if dog_name:
                        dog_names.add(dog_name)
                    
                    # Collect location name for later insertion
                    location = session_data.get('location')
                    if location:
                        location_names.add(location)
                    
                    # Insert into database
                    with database.get_connection() as conn:
                        # Convert image_files list to JSON string if present
                        image_files = session_data.get('image_files', [])
                        image_files_json = json.dumps(image_files) if isinstance(image_files, list) else (image_files or "")
                        
                        conn.execute(
                            text("""
                                INSERT INTO training_sessions 
                                (date, session_number, handler, session_purpose, field_support, dog_name, location,
                                 search_area_size, num_subjects, handler_knowledge, weather, temperature, 
                                 wind_direction, wind_speed, search_type, drive_level, subjects_found, comments, image_files, user_name)
                                VALUES (:date, :session_number, :handler, :session_purpose, :field_support, :dog_name, :location,
                                        :search_area_size, :num_subjects, :handler_knowledge, :weather, :temperature, 
                                        :wind_direction, :wind_speed, :search_type, :drive_level, :subjects_found, :comments, :image_files, :user_name)
                            """),
                            {
                                "date": session_data.get('date'),
                                "session_number": session_data.get('session_number'),
                                "handler": session_data.get('handler'),
                                "session_purpose": session_data.get('session_purpose'),
                                "field_support": session_data.get('field_support'),
                                "dog_name": session_data.get('dog_name'),
                                "location": session_data.get('location'),
                                "search_area_size": session_data.get('search_area_size'),
                                "num_subjects": session_data.get('num_subjects'),
                                "handler_knowledge": session_data.get('handler_knowledge'),
                                "weather": session_data.get('weather'),
                                "temperature": session_data.get('temperature'),
                                "wind_direction": session_data.get('wind_direction'),
                                "wind_speed": session_data.get('wind_speed'),
                                "search_type": session_data.get('search_type'),
                                "drive_level": session_data.get('drive_level'),
                                "subjects_found": session_data.get('subjects_found'),
                                "comments": session_data.get('comments', ''),
                                "image_files": image_files_json,
                                "user_name": session_data.get('user_name', get_username())
                            }
                        )
                        conn.commit()
                        
                        # Get the session_id we just inserted (for terrains and subject responses)
                        result = conn.execute(
                            text("SELECT id FROM training_sessions WHERE session_number = :session_number AND dog_name = :dog_name"),
                            {"session_number": session_data.get('session_number'), "dog_name": session_data.get('dog_name')}
                        )
                        session_row = result.fetchone()
                        
                        if session_row:
                            session_id = session_row[0]
                            
                            # Insert selected terrains if present in JSON
                            selected_terrains = session_data.get('selected_terrains', [])
                            for terrain_name in selected_terrains:
                                conn.execute(
                                    text("""
                                        INSERT INTO selected_terrains (session_id, terrain_name, user_name)
                                        VALUES (:session_id, :terrain_name, :user_name)
                                    """),
                                    {
                                        "session_id": session_id,
                                        "terrain_name": terrain_name,
                                        "user_name": session_data.get('user_name', get_username())
                                    }
                                )
                            
                            # Insert subject responses if present in JSON
                            subject_responses = session_data.get('subject_responses', [])
                            for response in subject_responses:
                                if isinstance(response, dict):
                                    conn.execute(
                                        text("""
                                            INSERT INTO subject_responses (session_id, subject_number, tfr, refind, user_name)
                                            VALUES (:session_id, :subject_number, :tfr, :refind, :user_name)
                                        """),
                                        {
                                            "session_id": session_id,
                                            "subject_number": response.get('subject_number'),
                                            "tfr": response.get('tfr', ''),
                                            "refind": response.get('refind', ''),
                                            "user_name": session_data.get('user_name', get_username())
                                        }
                                    )
                            
                            conn.commit()
                    
                    restored_count += 1
                    
                except Exception as e:
                    print(f"Failed to restore {json_file.name}: {e}")
                    failed_count += 1
            
            # Now insert all unique dog names into dogs table
            # print(f"DEBUG: Found {len(dog_names)} unique dogs in backups: {sorted(dog_names)}")  # DEBUG
            dogs_added = 0
            for dog_name in sorted(dog_names):
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                            {"name": dog_name, "user_name": get_username()}
                        )
                        conn.commit()
                    dogs_added += 1
                    # print(f"DEBUG: Added dog '{dog_name}' to dogs table")  # DEBUG
                except Exception as e:
                    # Dog might already exist (UNIQUE constraint), that's OK
                    if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                        # print(f"DEBUG: Dog '{dog_name}' already exists in dogs table")  # DEBUG
                        pass  # Duplicate is OK, continue with next dog
                    else:
                        # print(f"DEBUG: Failed to add dog '{dog_name}': {e}")  # DEBUG
                        pass  # Other errors are logged but don't stop the process
            
            # print(f"DEBUG: Added {dogs_added} new dogs to dogs table")  # DEBUG
            
            # Now insert all unique location names into training_locations table
            # print(f"DEBUG: Found {len(location_names)} unique locations in backups: {sorted(location_names)}")  # DEBUG
            locations_added = 0
            for location in sorted(location_names):
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                            {"name": location, "user_name": get_username()}
                        )
                        conn.commit()
                    locations_added += 1
                    # print(f"DEBUG: Added location '{location}' to training_locations table")  # DEBUG
                except Exception as e:
                    # Location might already exist (UNIQUE constraint), that's OK
                    if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                        # print(f"DEBUG: Location '{location}' already exists in training_locations table")  # DEBUG
                        pass  # Duplicate is OK, continue with next location
                    else:
                        # print(f"DEBUG: Failed to add location '{location}': {e}")  # DEBUG
                        pass  # Other errors are logged but don't stop the process
            
            # print(f"DEBUG: Added {locations_added} new locations to training_locations table")  # DEBUG
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Refresh dog list in UI
            self.load_dogs_from_database()
            if hasattr(self, 'dog_combo'):
                self.refresh_dog_list()
            
            # Refresh location list in UI
            self.load_locations_from_database()
            if hasattr(self, 'location_combo'):
                self.refresh_location_list()
            
            # Also try to restore from settings backup if it exists
            settings_restored = False
            terrain_added = 0
            distraction_added = 0
            
            settings_path = backup_path / "airscenting_settings.json"
            if settings_path.exists():
                try:
                    with open(settings_path, 'r') as f:
                        settings = json.load(f)
                    
                    # Insert terrain types
                    terrain_types = settings.get("terrain_types", [])
                    for terrain in terrain_types:
                        try:
                            with database.get_connection() as conn:
                                conn.execute(
                                    text("INSERT INTO terrain_types (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": terrain, "user_name": get_username()}
                                )
                                conn.commit()
                            terrain_added += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e) and "duplicate key" not in str(e):
                                print(f"Failed to add terrain type '{terrain}': {e}")
                    
                    # Insert distraction types
                    distraction_types = settings.get("distraction_types", [])
                    for distraction in distraction_types:
                        try:
                            with database.get_connection() as conn:
                                conn.execute(
                                    text("INSERT INTO distraction_types (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": distraction, "user_name": get_username()}
                                )
                                conn.commit()
                            distraction_added += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e) and "duplicate key" not in str(e):
                                print(f"Failed to add distraction type '{distraction}': {e}")
                    
                    # Refresh UI
                    self.load_terrain_from_database()
                    self.load_distraction_from_database()
                    # Also refresh Entry tab terrain combobox
                    if hasattr(self, 'terrain_combo'):
                        self.refresh_terrain_list()
                    
                    settings_restored = True
                    
                except Exception as e:
                    print(f"Could not restore settings backup: {e}")
            
            # Show results
            if restored_count > 0:
                msg = f"Successfully restored {restored_count} session(s)"
                if dogs_added > 0:
                    msg += f"\nAdded {dogs_added} dog(s) to database"
                if locations_added > 0:
                    msg += f"\nAdded {locations_added} location(s) to database"
                if settings_restored:
                    if terrain_added > 0:
                        msg += f"\nAdded {terrain_added} terrain type(s) from settings"
                    if distraction_added > 0:
                        msg += f"\nAdded {distraction_added} distraction type(s) from settings"
                if failed_count > 0:
                    msg += f"\n{failed_count} session(s) failed to restore"
                messagebox.showinfo("Restore Complete", msg)
                return True
            else:
                messagebox.showerror("Restore Failed", "No sessions were restored")
                return False
            
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
            
            messagebox.showerror("Restore Error", f"Failed to restore sessions:\n{e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
    
    def offer_load_default_types(self, db_type):
        """Offer to load default terrain and distraction types into new database"""
        result = messagebox.askyesno(
            "Load Default Types?",
            "Would you like to load the default terrain and distraction types?\n\n"
            "Terrain types (17):\n"
            "Urban, Rural, Forest, Scrub, Desert, Sandy, Rocky, City park, Meadow, etc.\n\n"
            "Distraction types (7):\n"
            "Critter, Horse, Loud noise, Motorcycle, Hikers, Cow, Vehicle"
        )
        
        if not result:
            return
        
        # Use DatabaseManager to properly load defaults with sort_order
        db_mgr = get_db_manager(db_type)
        
        # Show working dialog for networked databases
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.root, "Loading Defaults", 
                                         f"Loading default types to {db_type} database...")
            self.root.update()
        else:
            working_dialog = None
        
        try:
            terrain_success, terrain_msg = db_mgr.restore_default_terrain_types()
            distraction_success, distraction_msg = db_mgr.restore_default_distraction_types()
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
        
        # Refresh UI - both Setup tab AND Entry tab
        self.load_terrain_from_database()  # Setup tab treeview
        self.load_distraction_from_database()  # Setup tab treeview
        
        # CRITICAL: Also refresh Entry tab comboboxes!
        if hasattr(self, 'terrain_combo'):
            self.refresh_terrain_list()  # Entry tab terrain combobox
        
        # Show summary
        if terrain_success and distraction_success:
            messagebox.showinfo("Success", 
                f"{terrain_msg}\n{distraction_msg}")
        else:
            errors = []
            if not terrain_success:
                errors.append(f"Terrain: {terrain_msg}")
            if not distraction_success:
                errors.append(f"Distraction: {distraction_msg}")
            messagebox.showerror("Error", "\n".join(errors))
    
    def on_date_changed(self, event=None):
        """Called when date picker value changes"""
        selected_date = self.date_picker.get_date()
        self.date_var.set(selected_date.strftime("%Y-%m-%d"))
    
    def set_date(self, date_string):
        """Set the date in both date_var and date_picker widget"""
        try:
            # Parse the date string
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            # Update the DateEntry widget
            self.date_picker.set_date(date_obj)
            # Update the StringVar
            self.date_var.set(date_string)
        except ValueError:
            # If invalid date, use today
            today = datetime.now()
            self.date_picker.set_date(today)
            self.date_var.set(today.strftime("%Y-%m-%d"))
            
    def save_db_setting(self, key, value):
        """Save a setting to the database"""
        db_mgr = get_db_manager(self.db_type_var.get())
        db_mgr.save_setting(key, value) 
    
    def load_db_setting(self, key, default=None):
        """Load a setting from the database"""
        db_mgr = get_db_manager(self.db_type_var.get())
        return db_mgr.load_setting(key, default)
    
    def on_dog_changed(self, event=None):
        """Called when dog selection changes - update session number and clear form for new dog"""
        dog_name = self.dog_var.get()
        # print(f"DEBUG on_dog_changed: dog_name = '{dog_name}'")  # DEBUG
        if dog_name:
            db_type = self.db_type_var.get()
            
            # Show working dialog for networked databases
            if db_type in ["postgres", "supabase", "mysql"]:
                working_dialog = WorkingDialog(self.root, "Loading Dog Data", 
                                             f"Loading data for {dog_name}...")
                self.root.update()
            else:
                working_dialog = None
            
            try:
                # Save dog to database for persistence across sessions
                self.save_db_setting("last_dog_name", dog_name)
                
                # Update session number to next available for this dog
                next_session = self.get_next_session_number(dog_name)
                # print(f"DEBUG on_dog_changed: next_session = {next_session}")  # DEBUG
                self.session_var.set(str(next_session))
                
                # Clear form fields for new dog (like "New" button but keep handler and dog)
                self.set_date(datetime.now().strftime("%Y-%m-%d"))
                # handler_var is NOT cleared - keep current handler name
                self.purpose_var.set("")
                self.field_support_var.set("")
                # dog_var is already set - don't clear it
                self.location_var.set("")
                self.search_area_var.set("")
                self.num_subjects_var.set("")
                self.handler_knowledge_var.set("")
                self.weather_var.set("")
                self.temperature_var.set("")
                self.wind_direction_var.set("")
                self.wind_speed_var.set("")
                self.search_type_var.set("")
                self.drive_level_var.set("")
                self.subjects_found_var.set("")
                self.comments_text.delete("1.0", tk.END)
                # Clear terrain accumulator
                self.accumulated_terrains = []
                self.accumulated_terrain_combo['values'] = []
                self.accumulated_terrain_var.set("")
                self.accumulated_terrain_combo['state'] = 'disabled'  # Disable when cleared
                # Clear map files list
                self.map_files_list = []
                self.map_listbox.delete(0, tk.END)
                self.view_map_button.config(state=tk.DISABLED)
                self.delete_map_button.config(state=tk.DISABLED)
                # Update subjects_found combo state
                self.update_subjects_found()
                
                # Clear selected sessions - switching dogs exits navigation mode
                self.selected_sessions = []
                self.selected_sessions_index = -1
                
                # Update navigation buttons
                self.update_navigation_buttons()
                
                self.status_var.set(f"Switched to {dog_name} - Next session: #{next_session}")
                
            finally:
                if working_dialog:
                    working_dialog.close(delay_ms=200)  # 200ms delay for UI to update
    
    def ensure_db_ready(self):
        """Ensure database connection is ready (password set for networked DBs)"""
        db_type = self.db_type_var.get()
        if db_type in ["postgres", "supabase", "mysql"]:
            password = self.db_password_var.get().strip()
            
            # If password not loaded yet, try loading from encrypted storage
            if not password and hasattr(self, 'config'):
                from password_manager import get_decrypted_password, check_crypto_available
                if check_crypto_available():
                    saved_password = get_decrypted_password(self.config, db_type)
                    if saved_password:
                        self.db_password_var.set(saved_password)
                        password = saved_password
            
            # Set password in database config
            if password:
                self.set_db_password()

    
    def get_next_session_number(self, dog_name=None):
        """Get the next session number for the specified dog"""
        # Ensure database is ready (critical for networked databases)
        self.ensure_db_ready()
        
        # Handle the optional parameter
        if dog_name is None and hasattr(self, 'dog_var'):
            dog_name = self.dog_var.get()

        if not dog_name:
            return 1

        # Use DatabaseManager
        from ui_database import get_db_manager
        db_mgr = get_db_manager(self.db_type_var.get())
        return db_mgr.get_next_session_number(dog_name)
    
    def save_session(self):
        """Save the current training session"""
        # Get all form values
        date = self.date_picker.get_date().strftime("%Y-%m-%d")
        session_number = self.session_var.get()
        handler = self.handler_var.get()
        session_purpose = self.purpose_var.get()
        field_support = self.field_support_var.get()
        dog_name = self.dog_var.get().strip() if self.dog_var.get() else ""

        # Search parameters
        location = self.location_var.get()
        search_area_size = self.search_area_var.get()
        num_subjects = self.num_subjects_var.get()
        handler_knowledge = self.handler_knowledge_var.get()
        weather = self.weather_var.get()
        temperature = self.temperature_var.get()
        wind_direction = self.wind_direction_var.get()
        wind_speed = self.wind_speed_var.get()
        search_type = self.search_type_var.get()

        # Search results
        drive_level = self.drive_level_var.get()
        subjects_found = self.subjects_found_var.get()
        comments = self.comments_text.get("1.0", tk.END).strip()

        # Map/image files - store as JSON string
        image_files_json = json.dumps(self.map_files_list) if self.map_files_list else ""

        # Validate required fields
        if not date:
            messagebox.showwarning("Missing Data", "Please enter a date")
            return
        if not session_number:
            messagebox.showwarning("Missing Data", "Please enter a session number")
            return
        if not dog_name:
            messagebox.showwarning("Missing Data", "Please select a dog")
            return

        try:
            session_number = int(session_number)
        except ValueError:
            messagebox.showwarning("Invalid Data", "Session number must be a number")
            return

        # Prepare session data dict
        session_data = {
            "date": date,
            "session_number": session_number,
            "handler": handler,
            "session_purpose": session_purpose,
            "field_support": field_support,
            "dog_name": dog_name,
            "location": location,
            "search_area_size": search_area_size,
            "num_subjects": num_subjects,
            "handler_knowledge": handler_knowledge,
            "weather": weather,
            "temperature": temperature,
            "wind_direction": wind_direction,
            "wind_speed": wind_speed,
            "search_type": search_type,
            "drive_level": drive_level,
            "subjects_found": subjects_found,
            "comments": comments,
            "image_files": image_files_json
        }

        # Save to database using DatabaseManager
        db_mgr = get_db_manager(self.db_type_var.get())
        
        # Show working dialog for networked databases
        db_type = self.db_type_var.get()
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.root, "Saving", 
                                         f"Saving session to {db_type} database...")
            self.root.update()
        else:
            working_dialog = None
        
        try:
            success, message, session_id = db_mgr.save_session(session_data)

            if not success:
                messagebox.showerror("Database Error", message)
                return

            # Save selected terrains
            db_mgr.save_selected_terrains(session_id, self.accumulated_terrains)

            # Save subject responses
            subject_responses_list = []
            for i in range(1, 11):
                item_id = f'subject_{i}'
                tags = self.subject_responses_tree.item(item_id, 'tags')

                if 'enabled' in tags:
                    values = self.subject_responses_tree.item(item_id, 'values')
                    subject_responses_list.append({
                        "subject_number": i,
                        "tfr": values[1] if len(values) > 1 else '',
                        "refind": values[2] if len(values) > 2 else ''
                    })

            db_mgr.save_subject_responses(session_id, subject_responses_list)
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)

        # Save last handler name to config
        if handler:
            self.config["last_handler_name"] = handler
            self.save_config()

        # Save session to JSON backup
        session_backup_data = {
            **session_data,
            "subject_responses": subject_responses_list,
            "image_files": self.map_files_list,
            "selected_terrains": self.accumulated_terrains,
            "user_name": get_username()
        }
        self.save_session_to_json(session_backup_data)

        self.status_var.set(message)
        messagebox.showinfo("Success", message)

        # Auto-prepare for next entry
        self.session_var.set(str(self.get_next_session_number()))
        self.selected_sessions = []
        self.selected_sessions_index = -1

        # Clear form fields (keep handler and dog)
        self.set_date(datetime.now().strftime("%Y-%m-%d"))
        self.purpose_var.set("")
        self.field_support_var.set("")
        self.location_var.set("")
        self.search_area_var.set("")
        self.num_subjects_var.set("")
        self.handler_knowledge_var.set("")
        self.weather_var.set("")
        self.temperature_var.set("")
        self.wind_direction_var.set("")
        self.wind_speed_var.set("")
        self.search_type_var.set("")
        self.drive_level_var.set("")
        self.subjects_found_var.set("")
        self.comments_text.delete("1.0", tk.END)
        self.accumulated_terrains = []
        self.accumulated_terrain_combo['values'] = []
        self.accumulated_terrain_var.set("")
        self.accumulated_terrain_combo['state'] = 'disabled'  # Disable when cleared
        self.map_files_list = []
        self.map_listbox.delete(0, tk.END)
        self.view_map_button.config(state=tk.DISABLED)
        self.delete_map_button.config(state=tk.DISABLED)
        self.update_subjects_found()
        # Reset tree selection to subject 1 after clearing form
        self.reset_subject_responses_tree_selection()
        self.update_navigation_buttons()

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
        """Setup the Setup tab with all configuration options"""
        # Create scrollable frame
        canvas = tk.Canvas(self.setup_tab)
        scrollbar = ttk.Scrollbar(self.setup_tab, orient="vertical", command=canvas.yview)
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
        
        # Database Type Selection
        db_type_frame = tk.LabelFrame(frame, text="Database Type", padx=10, pady=5)
        db_type_frame.pack(fill="x", pady=5)
        
        self.db_type_var = tk.StringVar(value=self.config.get("db_type", "sqlite"))
        
        radio_container = tk.Frame(db_type_frame)
        radio_container.pack(pady=5)
        
        tk.Radiobutton(radio_container, text="SQLite", variable=self.db_type_var, 
                      value="sqlite", command=self.on_db_type_changed).pack(side="left", padx=20)
        tk.Radiobutton(radio_container, text="PostgreSQL", variable=self.db_type_var, 
                      value="postgres", command=self.on_db_type_changed).pack(side="left", padx=20)
        tk.Radiobutton(radio_container, text="Supabase", variable=self.db_type_var, 
                      value="supabase", command=self.on_db_type_changed).pack(side="left", padx=20)
        tk.Radiobutton(radio_container, text="MySQL", variable=self.db_type_var, 
                      value="mysql", command=self.on_db_type_changed).pack(side="left", padx=20)
        
        # Database Password (for postgres, supabase, mysql)
        self.db_password_frame = tk.Frame(db_type_frame)
        self.db_password_frame.pack(pady=5)
        
        tk.Label(self.db_password_frame, text="Database Password:").pack(side="left", padx=5)
        self.db_password_var = tk.StringVar()
        self.db_password_entry = tk.Entry(self.db_password_frame, textvariable=self.db_password_var, 
                                          width=30, show="*")
        self.db_password_entry.pack(side="left", padx=5)
        
        # Add right-click context menu for password entry (Cut/Copy/Paste)
        self.add_entry_context_menu(self.db_password_entry)
        
        # Show/Hide password checkbox
        self.show_password_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.db_password_frame, text="Show", variable=self.show_password_var,
                      command=self.toggle_password_visibility).pack(side="left", padx=5)
        
        # Remember Password checkbox
        self.remember_password_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.db_password_frame, text="Remember", variable=self.remember_password_var).pack(side="left", padx=5)
        
        # Forget Password button
        tk.Button(self.db_password_frame, text="Forget Saved Password", 
                 command=self.forget_password, width=18).pack(side="left", padx=5)
        
        # Add trace to update Create Database button when database type changes
        self.db_type_var.trace_add('write', self.update_create_db_button_state)
        
        # Initialize button state and password field visibility
        self.root.after(100, self.update_create_db_button_state)
        self.root.after(100, self.on_db_type_changed)
        
        # Database folder selection
        db_frame = tk.LabelFrame(frame, text="Database Folder", padx=10, pady=5)
        db_frame.pack(fill="x", pady=5)
        
        tk.Entry(db_frame, textvariable=self.db_path_var, width=70).pack(side="left", padx=5)
        tk.Button(db_frame, text="Browse", command=self.select_db_folder).pack(side="left", padx=5)
        self.create_db_btn = tk.Button(db_frame, text="Create Database", 
                                       command=self.create_database, state="disabled")
        self.create_db_btn.pack(side="left", padx=5)
        
        # Add trace to db_path_var to enable/disable Create Database button
        self.db_path_var.trace_add('write', self.update_create_db_button_state)
        
        # Trail maps folder
        folder_frame = tk.LabelFrame(frame, text="Trail Maps Storage Folder", padx=10, pady=5)
        folder_frame.pack(fill="x", pady=5)
        
        tk.Entry(folder_frame, textvariable=self.folder_path_var, width=70).pack(side="left", padx=5)
        tk.Button(folder_frame, text="Browse", command=self.select_folder).pack(side="left", padx=5)
        
        # Backup folder
        backup_frame = tk.LabelFrame(frame, text="Backup Folder", padx=10, pady=5)
        backup_frame.pack(fill="x", pady=5)
        
        tk.Entry(backup_frame, textvariable=self.backup_path_var, width=70).pack(side="left", padx=5)
        tk.Button(backup_frame, text="Browse", command=self.select_backup_folder).pack(side="left", padx=5)
        tk.Button(backup_frame, text="Restore Settings from Backup", 
                 command=self.restore_settings_from_json).pack(side="left", padx=5)
        
        # Default values
        defaults_frame = tk.LabelFrame(frame, text="Default Values (Optional)", padx=10, pady=5)
        defaults_frame.pack(fill="x", pady=5)
        
        tk.Label(defaults_frame, text="Handler Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.default_handler_var = tk.StringVar(value=self.config.get("handler_name", ""))
        tk.Entry(defaults_frame, textvariable=self.default_handler_var, width=30).grid(row=0, column=1, padx=5, pady=2)
        
        # Note about saving
        tk.Label(defaults_frame, text="(Click 'Save Configuration' button at bottom to save all settings)",
                font=("Helvetica", 8, "italic"), fg="gray").grid(row=1, column=0, columnspan=2, pady=5)
        
        # Container frame for the management sections (uses grid internally)
        management_container = tk.Frame(frame)
        management_container.pack(fill="both", expand=True, pady=5)
        
        # Create vertical container for column 0 (Training Locations and Dog Names)
        column0_container = tk.Frame(management_container)
        column0_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Training Locations Management
        locations_frame = tk.LabelFrame(column0_container, text="Training Locations", padx=10, pady=5)
        locations_frame.pack(fill="x", pady=(0, 5))
        
        # Listbox with scrollbar
        loc_list_frame = tk.Frame(locations_frame)
        loc_list_frame.pack(side="left", fill="both", expand=True)
        
        loc_scrollbar = tk.Scrollbar(loc_list_frame)
        loc_scrollbar.pack(side="right", fill="y")
        
        self.location_listbox = tk.Listbox(loc_list_frame, yscrollcommand=loc_scrollbar.set, height=4)
        self.location_listbox.pack(side="left", fill="both", expand=True)
        loc_scrollbar.config(command=self.location_listbox.yview)
        
        # Populate listbox with locations from database
        self.load_locations_from_database()
        
        # Buttons for managing locations
        loc_button_frame = tk.Frame(locations_frame)
        loc_button_frame.pack(side="right", padx=(10, 0))
        
        tk.Label(loc_button_frame, text="Location:").pack(anchor="w")
        self.new_location_var = tk.StringVar()
        location_entry = tk.Entry(loc_button_frame, textvariable=self.new_location_var, width=20)
        location_entry.pack(pady=2)
        location_entry.bind('<Return>', lambda e: self.add_location())
        
        self.add_location_btn = tk.Button(loc_button_frame, text="Add Location", 
                                         command=self.add_location, width=15, state="disabled")
        self.add_location_btn.pack(pady=2)
        
        self.remove_location_btn = tk.Button(loc_button_frame, text="Remove Selected", 
                                            command=self.remove_location, width=15, state="disabled")
        self.remove_location_btn.pack(pady=2)
        
        # Add trace and selection binding for locations
        self.new_location_var.trace_add('write', self.update_location_button_states)
        self.location_listbox.bind('<<ListboxSelect>>', self.on_location_select)
        
        # Dog Names Management
        dogs_frame = tk.LabelFrame(column0_container, text="Dog Names", padx=10, pady=5)
        dogs_frame.pack(fill="x")
        
        # Listbox with scrollbar
        list_frame = tk.Frame(dogs_frame)
        list_frame.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.dog_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=3)
        self.dog_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.dog_listbox.yview)
        
        # Populate listbox with dogs from database
        self.load_dogs_from_database()
        
        # Buttons for managing dogs
        button_frame = tk.Frame(dogs_frame)
        button_frame.pack(side="right", padx=(10, 0))
        
        tk.Label(button_frame, text="Dog Name:").pack(anchor="w")
        self.new_dog_var = tk.StringVar()
        dog_entry = tk.Entry(button_frame, textvariable=self.new_dog_var, width=20)
        dog_entry.pack(pady=2)
        dog_entry.bind('<Return>', lambda e: self.add_dog())
        
        self.add_dog_btn = tk.Button(button_frame, text="Add Dog", 
                                     command=self.add_dog, width=15, state="disabled")
        self.add_dog_btn.pack(pady=2)
        
        self.remove_dog_btn = tk.Button(button_frame, text="Remove Selected", 
                                       command=self.remove_dog, width=15, state="disabled")
        self.remove_dog_btn.pack(pady=2)
        
        # Add trace to entry field and bind listbox selection
        self.new_dog_var.trace_add('write', self.update_dog_button_states)
        self.dog_listbox.bind('<<ListboxSelect>>', self.on_dog_select)
        
        # Terrain Types Management
        terrain_frame = tk.LabelFrame(management_container, text="Terrain Types", padx=10, pady=5)
        terrain_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Treeview with scrollbar
        tree_frame = tk.Frame(terrain_frame)
        tree_frame.pack(side="left", fill="both", expand=True)
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")
        
        self.terrain_tree = ttk.Treeview(tree_frame, columns=('Terrain',), show='tree headings', 
                                        yscrollcommand=tree_scrollbar.set, height=8, selectmode='browse')
        self.terrain_tree.heading('#0', text='#')
        self.terrain_tree.heading('Terrain', text='Terrain Type')
        self.terrain_tree.column('#0', width=40)
        self.terrain_tree.column('Terrain', width=150)
        self.terrain_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.config(command=self.terrain_tree.yview)
        
        # Populate treeview with terrain types from database
        self.load_terrain_from_database()
        
        # Buttons for managing terrain types
        terrain_button_frame = tk.Frame(terrain_frame)
        terrain_button_frame.pack(side="right", padx=(10, 0))
        
        tk.Label(terrain_button_frame, text="Terrain Type:").pack(anchor="w")
        self.new_terrain_var = tk.StringVar()
        terrain_entry = tk.Entry(terrain_button_frame, textvariable=self.new_terrain_var, width=20)
        terrain_entry.pack(pady=2)
        terrain_entry.bind('<Return>', lambda e: self.add_terrain_type())
        
        self.add_terrain_btn = tk.Button(terrain_button_frame, text="Add Terrain Type", 
                                        command=self.add_terrain_type, width=15, state="disabled")
        self.add_terrain_btn.pack(pady=2)
        
        self.remove_terrain_btn = tk.Button(terrain_button_frame, text="Remove Selected", 
                                           command=self.remove_terrain_type, width=15, state="disabled")
        self.remove_terrain_btn.pack(pady=2)
        
        self.move_terrain_up_btn = tk.Button(terrain_button_frame, text="Move Up", 
                                            command=self.move_terrain_up, width=15, state="disabled")
        self.move_terrain_up_btn.pack(pady=2)
        
        self.move_terrain_down_btn = tk.Button(terrain_button_frame, text="Move Down", 
                                              command=self.move_terrain_down, width=15, state="disabled")
        self.move_terrain_down_btn.pack(pady=2)
        
        tk.Button(terrain_button_frame, text="Restore Defaults", 
                 command=self.restore_default_terrain_types, width=15).pack(pady=2)
        
        # Add trace and selection binding
        self.new_terrain_var.trace_add('write', self.update_terrain_button_states)
        self.terrain_tree.bind('<<TreeviewSelect>>', self.on_terrain_select)
        
        # Distraction Types Management
        distraction_frame = tk.LabelFrame(management_container, text="Distraction Types", padx=10, pady=5)
        distraction_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        # Treeview with scrollbar
        dist_tree_frame = tk.Frame(distraction_frame)
        dist_tree_frame.pack(side="left", fill="both", expand=True)
        
        dist_tree_scrollbar = ttk.Scrollbar(dist_tree_frame, orient="vertical")
        dist_tree_scrollbar.pack(side="right", fill="y")
        
        self.distraction_type_tree = ttk.Treeview(dist_tree_frame, columns=('Distraction',), show='tree headings', 
                                                 yscrollcommand=dist_tree_scrollbar.set, height=8, selectmode='browse')
        self.distraction_type_tree.heading('#0', text='#')
        self.distraction_type_tree.heading('Distraction', text='Distraction Type')
        self.distraction_type_tree.column('#0', width=40)
        self.distraction_type_tree.column('Distraction', width=150)
        self.distraction_type_tree.pack(side="left", fill="both", expand=True)
        dist_tree_scrollbar.config(command=self.distraction_type_tree.yview)
        
        # Populate treeview with distraction types from database
        self.load_distraction_from_database()
        
        # Buttons for managing distraction types
        distraction_button_frame = tk.Frame(distraction_frame)
        distraction_button_frame.pack(side="right", padx=(10, 0))
        
        tk.Label(distraction_button_frame, text="Distraction Type:").pack(anchor="w")
        self.new_distraction_var = tk.StringVar()
        distraction_entry = tk.Entry(distraction_button_frame, textvariable=self.new_distraction_var, width=20)
        distraction_entry.pack(pady=2)
        distraction_entry.bind('<Return>', lambda e: self.add_distraction_type())
        
        self.add_distraction_type_btn = tk.Button(distraction_button_frame, text="Add Distraction Type", 
                                                 command=self.add_distraction_type, width=17, state="disabled")
        self.add_distraction_type_btn.pack(pady=2)
        
        self.remove_distraction_type_btn = tk.Button(distraction_button_frame, text="Remove Selected", 
                                                    command=self.remove_distraction_type, width=17, state="disabled")
        self.remove_distraction_type_btn.pack(pady=2)
        
        self.move_distraction_type_up_btn = tk.Button(distraction_button_frame, text="Move Up", 
                                                     command=self.move_distraction_up, width=17, state="disabled")
        self.move_distraction_type_up_btn.pack(pady=2)
        
        self.move_distraction_type_down_btn = tk.Button(distraction_button_frame, text="Move Down", 
                                                       command=self.move_distraction_down, width=17, state="disabled")
        self.move_distraction_type_down_btn.pack(pady=2)
        
        tk.Button(distraction_button_frame, text="Restore Defaults", 
                 command=self.restore_default_distraction_types, width=17).pack(pady=2)
        
        # Add trace and selection binding
        self.new_distraction_var.trace_add('write', self.update_distraction_type_button_states)
        self.distraction_type_tree.bind('<<TreeviewSelect>>', self.on_distraction_type_select)
        
        # Configure grid weights so they expand properly
        management_container.grid_columnconfigure(0, weight=1)
        management_container.grid_columnconfigure(1, weight=1)
        management_container.grid_columnconfigure(2, weight=1)
        
        # Save Configuration Button
        save_config_frame = tk.Frame(frame)
        save_config_frame.pack(pady=20)
        
        tk.Button(save_config_frame, text="💾 Save Configuration",
                 command=self.save_configuration_settings,
                 bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"),
                 width=30, height=2).pack()
        
        tk.Label(save_config_frame, text="Save all file paths and settings to config file",
                font=("Helvetica", 9, "italic"), fg="gray").pack(pady=(5, 0))
    
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
        self.date_picker = DateEntry(
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
        self.date_picker.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        # Create StringVar to track the date for compatibility with existing code
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        # Bind date picker changes to update the StringVar
        self.date_picker.bind("<<DateEntrySelected>>", self.on_date_changed)
        
        tk.Label(session_frame, text="Session #:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        # Initialize with "1" for now, will update after password is loaded
        self.session_var = tk.StringVar(value="1")
        self.session_entry = tk.Entry(session_frame, textvariable=self.session_var, width=10)
        self.session_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        self.session_entry.bind("<FocusOut>", self.on_session_number_changed)
        self.session_entry.bind("<Return>", self.on_session_number_changed)
        tk.Button(session_frame, text="New", command=self.new_session).grid(row=0, column=4, padx=5)
        
        tk.Button(session_frame, text="Edit/Delete Prior Session", command=self.load_prior_session, 
                 bg="#4169E1", fg="white").grid(row=0, column=5, padx=5, pady=2)
        
        # Previous and Next session navigation buttons
        self.prev_session_btn = tk.Button(session_frame, text="◀ Previous", bg="#FF8C00", fg="white",
                                         width=10, command=self.navigate_previous_session, state=tk.DISABLED)
        self.prev_session_btn.grid(row=0, column=6, padx=2, pady=2)
        self.next_session_btn = tk.Button(session_frame, text="Next ▶", bg="#FF8C00", fg="white",
                                         width=10, command=self.navigate_next_session, state=tk.DISABLED)
        self.next_session_btn.grid(row=0, column=7, padx=2, pady=2)
        
        # Export PDF button
        tk.Button(session_frame, text="Export PDF", bg="#9370DB", fg="white", width=12, 
                 command=self.open_export_dialog).grid(row=0, column=8, padx=2, pady=2)
        
        # Track selected sessions for navigation
        self.selected_sessions = []  # List of session numbers to navigate through
        self.selected_sessions_index = -1  # Current position in selected sessions
        
        # Row 1: Handler, Session Purpose, Field Support, Dog
        tk.Label(session_frame, text="Handler:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        # If handler_name is set, use it; otherwise use last_handler_name
        default_handler = self.config.get("handler_name", "") or self.config.get("last_handler_name", "")
        self.handler_var = tk.StringVar(value=default_handler)
        tk.Entry(session_frame, textvariable=self.handler_var, width=15).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Session Purpose:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.purpose_var = tk.StringVar()
        purpose_combo = ttk.Combobox(session_frame, textvariable=self.purpose_var, width=22,
                                     values=['Area Search Training', 'Refind Training', 
                                            'Motivational Training', 
                                            'Obedience', 'Mock Certification Test', 'Mission'])
        purpose_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Field Support:").grid(row=1, column=4, sticky="w", padx=5, pady=2)
        self.field_support_var = tk.StringVar()
        tk.Entry(session_frame, textvariable=self.field_support_var, width=25).grid(row=1, column=5, sticky="w", padx=5, pady=2)
        
        tk.Label(session_frame, text="Dog:").grid(row=1, column=6, sticky="e", padx=5, pady=2)
        # Load last dog from database (not config)
        last_dog = self.load_db_setting("last_dog_name", "")
        self.dog_var = tk.StringVar(value=last_dog)
        self.dog_combo = ttk.Combobox(session_frame, textvariable=self.dog_var, width=15, state="readonly")
        # Load dogs from database
        self.refresh_dog_list()
        self.dog_combo.grid(row=1, column=7, sticky="w", padx=5, pady=2)
        # Bind dog change to update session number
        self.dog_combo.bind('<<ComboboxSelected>>', self.on_dog_changed)
        
        # Search Parameters
        search_frame = tk.LabelFrame(frame, text="Search Parameters", padx=10, pady=5)
        search_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        
        tk.Label(search_frame, text="Location:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(search_frame, textvariable=self.location_var, width=18, state="readonly")
        self.location_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        # Load locations from database
        self.refresh_location_list()
        
        tk.Label(search_frame, text="Search Area (Acres):").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.search_area_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.search_area_var, width=18).grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Number of Subjects:").grid(row=0, column=4, sticky="w", padx=5, pady=2)
        self.num_subjects_var = tk.StringVar()
        self.num_subjects_combo = ttk.Combobox(search_frame, textvariable=self.num_subjects_var, width=15, state="readonly",
                                     values=['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
        self.num_subjects_combo.grid(row=0, column=5, sticky="w", padx=5, pady=2)
        self.num_subjects_combo.bind('<<ComboboxSelected>>', self.update_subjects_found)
        
        tk.Label(search_frame, text="Handler Knowledge:").grid(row=0, column=6, sticky="w", padx=5, pady=2)
        self.handler_knowledge_var = tk.StringVar()
        handler_knowledge_combo = ttk.Combobox(search_frame, textvariable=self.handler_knowledge_var, width=25, state="readonly",
                                              values=['Unknown number of subjects', 'Number of subjects known'])
        handler_knowledge_combo.grid(row=0, column=7, columnspan=2, sticky="w", padx=5, pady=2)
        
        # Row 1: Weather, Wind Direction, Wind Speed
        tk.Label(search_frame, text="Weather:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.weather_var = tk.StringVar()
        weather_combo = ttk.Combobox(search_frame, textvariable=self.weather_var, width=18, state="readonly",
                                     values=['Clear', 'Cloudy', 'Light Rain', 'Heavy Rain', 
                                            'Snow Cover', 'Snowing', 'Fog'])
        weather_combo.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Wind Direction:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.wind_direction_var = tk.StringVar()
        wind_dir_combo = ttk.Combobox(search_frame, textvariable=self.wind_direction_var, width=15, state="readonly",
                                      values=['North', 'South', 'East', 'West', 
                                             'NE', 'NW', 'SE', 'SW', 'Variable'])
        wind_dir_combo.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Wind Speed:").grid(row=1, column=4, sticky="w", padx=5, pady=2)
        self.wind_speed_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.wind_speed_var, width=18).grid(row=1, column=5, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Search Type:").grid(row=1, column=6, sticky="w", padx=5, pady=2)
        self.search_type_var = tk.StringVar()
        search_type_combo = ttk.Combobox(search_frame, textvariable=self.search_type_var, width=25, state="readonly",
                                        values=['Single blind', 'Double blind', 'Subject coordinates known'])
        search_type_combo.grid(row=1, column=7, sticky="w", padx=5, pady=2)
        
        # Row 2: Temperature, Terrain Type
        tk.Label(search_frame, text="Temperature:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.temperature_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.temperature_var, width=21).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(search_frame, text="Add Terrain Type:").grid(row=2, column=2, sticky="w", padx=5, pady=2)
        self.terrain_var = tk.StringVar()
        # Load terrain types from database using DatabaseManager (respects sort_order)
        from ui_database import get_db_manager
        db_mgr = get_db_manager(self.db_type_var.get())
        terrain_types = db_mgr.load_terrain_types()
        
        self.terrain_combo = ttk.Combobox(search_frame, textvariable=self.terrain_var, width=15, state="readonly",
                                         values=terrain_types)
        self.terrain_combo.grid(row=2, column=3, sticky="w", padx=5, pady=2)
        self.terrain_combo.bind('<<ComboboxSelected>>', self.add_to_terrain_accumulator)
        
        # Combobox for accumulated terrain types
        tk.Label(search_frame, text="Selected Terrains:").grid(row=2, column=4, sticky="w", padx=5, pady=2)
        self.accumulated_terrain_var = tk.StringVar()
        self.accumulated_terrain_combo = ttk.Combobox(search_frame, textvariable=self.accumulated_terrain_var, 
                                                      width=15, state="disabled", values=[])  # Start disabled
        self.accumulated_terrain_combo.grid(row=2, column=5, sticky="w", padx=5, pady=2)
        self.accumulated_terrain_combo.bind('<<ComboboxSelected>>', self.remove_terrain_from_list)
        
        # Add tooltip to accumulated terrain combobox
        from tips import ToolTip
        ToolTip(self.accumulated_terrain_combo, "Terrain List Accumulator\nClick an entry to remove from list", delay=750)
        
        # Track accumulated terrains as a list
        self.accumulated_terrains = []
        
        # Search Results
        results_frame = tk.LabelFrame(frame, text="Search Results", padx=10, pady=5)
        results_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        
        tk.Label(results_frame, text="Drive Level:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.drive_level_var = tk.StringVar()
        drive_level_combo = ttk.Combobox(results_frame, textvariable=self.drive_level_var, width=39, state="readonly",
                                        values=['High - Needed no encouragement',
                                               'Medium - Needed occasional encouragement',
                                               'Low - Needed frequent encouragement',
                                               'Would not work'])
        drive_level_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        tk.Label(results_frame, text="Subjects Found:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.subjects_found_var = tk.StringVar()
        self.subjects_found_combo = ttk.Combobox(results_frame, textvariable=self.subjects_found_var, width=15, state="readonly")
        self.subjects_found_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        # Add tooltip that only shows when subjects_found is disabled
        ConditionalToolTip(self.subjects_found_combo, 
                          "Enter number of subjects found (in Search Parameters)", 
                          show_when_disabled=True)
        
        # Bind to update subject responses grid when subjects found changes
        self.subjects_found_combo.bind('<<ComboboxSelected>>', self.update_subject_responses_grid)
        
        # Subject Responses Treeview (row 0, columns 4-7, rowspan=2) - no LabelFrame wrapper
        # Create container with scrollbar for the treeview
        tree_container = tk.Frame(results_frame)
        tree_container.grid(row=0, column=4, columnspan=4, rowspan=2, sticky="nsew", padx=5, pady=5)
        
        # Scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_container, orient="vertical")
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview - 3 visible rows (4th row requires scrolling)
        self.subject_responses_tree = ttk.Treeview(
            tree_container,
            columns=('subject', 'tfr', 'refind'),
            show='headings',
            height=3,
            yscrollcommand=tree_scrollbar.set,
            selectmode='browse'
        )
        self.subject_responses_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.config(command=self.subject_responses_tree.yview)
        
        # Configure columns
        self.subject_responses_tree.heading('subject', text='Subject #')
        self.subject_responses_tree.heading('tfr', text='TFR')
        self.subject_responses_tree.heading('refind', text='Re-find')
        
        self.subject_responses_tree.column('subject', width=80, anchor='center')
        self.subject_responses_tree.column('tfr', width=150, anchor='w')
        self.subject_responses_tree.column('refind', width=150, anchor='w')
        
        # Pre-populate with 10 empty/disabled rows to support up to 10 subjects
        for i in range(1, 11):
            # Determine odd/even for alternating shading
            row_tag = 'odd' if i % 2 == 1 else 'even'
            self.subject_responses_tree.insert('', tk.END, iid=f'subject_{i}',
                                              values=(f'Subject {i}', '', ''),
                                              tags=(row_tag, 'disabled'))
        
        # Style for alternating rows
        self.subject_responses_tree.tag_configure('odd', background='#f0f0f0')  # Light gray
        self.subject_responses_tree.tag_configure('even', background='#ffffff')  # White
        
        # Style for enabled/disabled (text color only, preserves background)
        self.subject_responses_tree.tag_configure('disabled', foreground='gray')
        self.subject_responses_tree.tag_configure('enabled', foreground='black')
        
        # Bind single-click to edit with inline combobox
        self.subject_responses_tree.bind('<Button-1>', self.on_treeview_click)
        
        # Add tooltip to explain how to edit cells
        ToolTip(self.subject_responses_tree, 
                "Click cell under desired heading on desired row to edit value", 
                delay=750)
        
        # TFR and Re-find options for editing
        self.tfr_options = ['Strong', 'Fair', 'Required cueing', 'None']
        self.refind_options = ['Immediate', 'Required cue', 'None']
        
        # Track current editing combobox
        self.tree_edit_combo = None
        self.tree_edit_item = None
        self.tree_edit_column = None
        
        # Comments textbox (row 1, columns 0-3) - below Drive Level/Subjects Found, aligns with bottom of Subject Responses
        self.comments_text = tk.Text(results_frame, width=60, height=3, wrap=tk.WORD)
        self.comments_text.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=(0, 5))
        ToolTip(self.comments_text, "Enter comments about search here")
        
        # Maps and Images
        map_frame = tk.LabelFrame(frame, text="Maps and Images", padx=10, pady=5)
        map_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        
        # Create container for drag-drop and listbox side by side
        map_container = tk.Frame(map_frame)
        map_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - Drag and drop area
        drop_frame = tk.Frame(map_container)
        drop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.drop_label = tk.Label(
            drop_frame,
            text="Drag & Drop Maps/Images\n(PDF/JPG/PNG)",
            bg="#e0e0e0",
            relief="ridge",
            height=4
        )
        self.drop_label.pack(fill=tk.BOTH, expand=True)
        
        # Enable drag and drop
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self.handle_drop)
        self.drop_label.dnd_bind('<<DragEnter>>', self.drag_enter)
        self.drop_label.dnd_bind('<<DragLeave>>', self.drag_leave)
        
        # Right side - Listbox with scrollbar and view button
        list_frame = tk.Frame(map_container)
        list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Container for listbox and buttons on same row
        list_button_container = tk.Frame(list_frame)
        list_button_container.pack(fill=tk.BOTH, expand=True)
        
        listbox_container = tk.Frame(list_button_container)
        listbox_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.map_listbox = tk.Listbox(listbox_container, height=3, font=('Arial', 9))
        map_scroll = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL,
                                   command=self.map_listbox.yview)
        self.map_listbox.config(yscrollcommand=map_scroll.set)
        
        self.map_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        map_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to open file
        self.map_listbox.bind('<Double-Button-1>', lambda e: self.view_selected_map())
        
        # Button frame to the right of listbox
        map_button_frame = tk.Frame(list_button_container)
        map_button_frame.pack(side=tk.RIGHT, padx=(5, 0))
        
        # View button
        self.view_map_button = tk.Button(map_button_frame, text="View Selected", 
                                         command=self.view_selected_map, state=tk.DISABLED, width=12)
        self.view_map_button.pack(pady=(0, 2))
        
        # Delete button
        self.delete_map_button = tk.Button(map_button_frame, text="Delete Selected", 
                                         command=self.delete_selected_map, state=tk.DISABLED, width=12)
        self.delete_map_button.pack(pady=(2, 0))
        
        self.map_files_list = []  # Store list of files
        
        # Bottom buttons
        button_frame = tk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=20)
        
        tk.Button(button_frame, text="Save Session", command=self.save_session,
                 bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"),
                 width=25, height=2).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Clear Form", command=self.clear_form,
                 width=15).pack(side="left", padx=10)
        
        tk.Button(button_frame, text="Quit", command=self.root.quit,
                 width=10).pack(side="left", padx=10)
        
        # Initialize navigation button states
        self.root.after(500, self.update_navigation_buttons)
        
        # Initialize subjects_found as disabled (no subjects selected yet)
        self.subjects_found_combo['state'] = 'disabled'
    
    # Placeholder methods for Entry tab buttons
    def clear_form(self):
        """Clear the form"""
        result = messagebox.askyesno("Clear Form", "Are you sure you want to clear all fields?")
        if result:
            self.set_date(datetime.now().strftime("%Y-%m-%d"))
            self.session_var.set(str(self.get_next_session_number()))
            # handler_var is NOT cleared - keep current handler name
            self.purpose_var.set("")
            self.field_support_var.set("")
            # dog_var is NOT cleared - keep current dog (persists)
            self.location_var.set("")
            self.search_area_var.set("")
            self.num_subjects_var.set("")
            self.handler_knowledge_var.set("")
            self.weather_var.set("")
            self.temperature_var.set("")
            self.wind_direction_var.set("")
            self.wind_speed_var.set("")
            self.search_type_var.set("")
            self.drive_level_var.set("")
            self.subjects_found_var.set("")
            self.comments_text.delete("1.0", tk.END)
            # Clear terrain accumulator
            self.accumulated_terrains = []
            self.accumulated_terrain_combo['values'] = []
            self.accumulated_terrain_var.set("")
            self.accumulated_terrain_combo['state'] = 'disabled'  # Disable when cleared
            # Update subjects_found combo state (will disable since num_subjects is blank)
            self.update_subjects_found()
            self.status_var.set("Form cleared")
            self.update_navigation_buttons()
    
    def new_session(self):
        """Advance to first available new session (MAX + 1)"""
        # Check for unsaved changes first
        if not self.check_entry_tab_changes():
            return
        
        next_session = self.get_next_session_number()
        self.session_var.set(str(next_session))
        # Clear selected sessions - we're starting fresh
        self.selected_sessions = []
        self.selected_sessions_index = -1
        # Clear form fields for new entry (KEEP handler name and dog name)
        self.set_date(datetime.now().strftime("%Y-%m-%d"))
        # handler_var is NOT cleared - keep current handler name
        self.purpose_var.set("")
        self.field_support_var.set("")
        # dog_var is NOT cleared - keep current dog (persists across sessions)
        self.location_var.set("")
        self.search_area_var.set("")
        self.num_subjects_var.set("")
        self.handler_knowledge_var.set("")
        self.weather_var.set("")
        self.temperature_var.set("")
        self.wind_direction_var.set("")
        self.wind_speed_var.set("")
        self.search_type_var.set("")
        self.drive_level_var.set("")
        self.subjects_found_var.set("")
        self.comments_text.delete("1.0", tk.END)
        # Clear terrain accumulator
        self.accumulated_terrains = []
        self.accumulated_terrain_combo['values'] = []
        self.accumulated_terrain_var.set("")
        self.accumulated_terrain_combo['state'] = 'disabled'  # Disable when cleared
        # Clear map files list
        self.map_files_list = []
        self.map_listbox.delete(0, tk.END)
        self.view_map_button.config(state=tk.DISABLED)
        self.delete_map_button.config(state=tk.DISABLED)
        # Update subjects_found combo state (will disable since num_subjects is blank)
        self.update_subjects_found()
        # Reset tree selection to subject 1
        self.reset_subject_responses_tree_selection()
        self.status_var.set(f"New session #{next_session}")
        self.update_navigation_buttons()
    
    def check_entry_tab_changes(self):
        """Check for unsaved changes in Entry tab. Returns True if OK to proceed."""
        # Get current form state
        current_date = self.date_var.get()
        current_session = self.session_var.get()
        current_handler = self.handler_var.get()
        current_purpose = self.purpose_var.get()
        current_field_support = self.field_support_var.get()
        current_dog = self.dog_var.get()
        current_search_area = self.search_area_var.get()
        current_num_subjects = self.num_subjects_var.get()
        current_handler_knowledge = self.handler_knowledge_var.get()
        current_weather = self.weather_var.get()
        current_temperature = self.temperature_var.get()
        current_wind_direction = self.wind_direction_var.get()
        current_wind_speed = self.wind_speed_var.get()
        current_search_type = self.search_type_var.get()
        current_drive_level = self.drive_level_var.get()
        current_subjects_found = self.subjects_found_var.get()
        
        # Check if this session exists in database and compare
        try:
            session_num = int(current_session)
        except ValueError:
            return True  # Invalid session number, OK to proceed
        
        db_type = self.db_type_var.get()
        
        try:
            # Get data from database
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            from sqlalchemy import text
            
            with database.get_connection() as conn:
                result = conn.execute(
                    text("""
                        SELECT date, handler, session_purpose, field_support, dog_name,
                               search_area_size, num_subjects, handler_knowledge, weather, temperature,
                               wind_direction, wind_speed, search_type, drive_level, subjects_found
                        FROM training_sessions 
                        WHERE session_number = :session_number
                    """),
                    {"session_number": session_num}
                )
                row = result.fetchone()
            
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            if row:
                # Compare with current values
                db_date = str(row[0]) if row[0] else ""
                db_handler = row[1] or ""
                db_purpose = row[2] or ""
                db_field_support = row[3] or ""
                db_dog = row[4] or ""
                db_search_area = row[5] or ""
                db_num_subjects = row[6] or ""
                db_handler_knowledge = row[7] or ""
                db_weather = row[8] or ""
                db_temperature = row[9] or ""
                db_wind_direction = row[10] or ""
                db_wind_speed = row[11] or ""
                db_search_type = row[12] or ""
                db_drive_level = row[13] or ""
                db_subjects_found = row[14] or ""
                
                if (current_date != db_date or
                    current_handler != db_handler or
                    current_purpose != db_purpose or
                    current_field_support != db_field_support or
                    current_dog != db_dog or
                    current_search_area != db_search_area or
                    current_num_subjects != db_num_subjects or
                    current_handler_knowledge != db_handler_knowledge or
                    current_weather != db_weather or
                    current_temperature != db_temperature or
                    current_wind_direction != db_wind_direction or
                    current_wind_speed != db_wind_speed or
                    current_search_type != db_search_type or
                    current_drive_level != db_drive_level or
                    current_subjects_found != db_subjects_found):
                    
                    # Changes detected
                    result = messagebox.askyesnocancel(
                        "Unsaved Changes",
                        f"You have unsaved changes to Session #{session_num}.\n\n"
                        "Do you want to save before proceeding?",
                        icon='warning'
                    )
                    
                    if result is None:  # Cancel
                        return False
                    elif result:  # Yes - save first
                        save_session()
                        return True
                    else:  # No - discard changes
                        return True
            
            # No changes or new session
            return True
            
        except Exception as e:
            # If error checking, just proceed
            try:
                import config
                import database
                from importlib import reload
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                pass
            
            return True
    
    def on_session_number_changed(self, event=None):
        """Called when session number field loses focus or user presses Enter"""
        # Clear selected sessions when manually changing session number
        self.selected_sessions = []
        self.selected_sessions_index = -1
        
        try:
            session_num = int(self.session_var.get())
            if session_num < 1:
                messagebox.showwarning("Invalid Session", "Session number must be at least 1")
                self.session_var.set("1")
                return
            
            max_session = self.get_next_session_number() - 1  # Current max
            if session_num > max_session + 1:
                messagebox.showwarning(
                    "Session Too High", 
                    f"Session #{session_num} doesn't exist.\n\n"
                    f"Maximum session is #{max_session}.\n"
                    f"Next available is #{max_session + 1}."
                )
                self.session_var.set(str(max_session + 1))
                return
            
            # Load session data if it exists
            self.load_session_by_number(session_num)
            self.update_navigation_buttons()
            
        except ValueError:
            messagebox.showwarning("Invalid Number", "Session number must be a valid number")
            self.session_var.set(str(self.get_next_session_number()))
    
    def load_session_by_number(self, session_number):
        """Load session data from database by session number and current dog"""
        if not hasattr(self, 'dog_var'):
            print("Warning: load_session_by_number called before dog_var initialized")
            return

        dog_name = self.dog_var.get().strip() if self.dog_var.get() else ""

        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first")
            return

        # Load session from database
        db_mgr = get_db_manager(self.db_type_var.get())
        
        # Show working dialog for networked databases
        db_type = self.db_type_var.get()
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.root, "Loading", 
                                         f"Loading session from {db_type} database...")
            self.root.update()
        else:
            working_dialog = None
        
        try:
            session_data = db_mgr.load_session(session_number, dog_name)
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)

        if session_data:
            # Populate form with session data
            self.set_date(session_data["date"])
            self.handler_var.set(session_data["handler"])
            self.purpose_var.set(session_data["session_purpose"])
            self.field_support_var.set(session_data["field_support"])
            self.dog_var.set(session_data["dog_name"])
            self.location_var.set(session_data["location"])
            self.search_area_var.set(session_data["search_area_size"])
            self.num_subjects_var.set(session_data["num_subjects"])
            self.handler_knowledge_var.set(session_data["handler_knowledge"])
            self.weather_var.set(session_data["weather"])
            self.temperature_var.set(session_data["temperature"])
            self.wind_direction_var.set(session_data["wind_direction"])
            self.wind_speed_var.set(session_data["wind_speed"])
            self.search_type_var.set(session_data["search_type"])
            self.drive_level_var.set(session_data["drive_level"])
            self.subjects_found_var.set(session_data["subjects_found"])

            # Load comments
            self.comments_text.delete("1.0", tk.END)
            self.comments_text.insert("1.0", session_data["comments"])

            # Load image files
            if session_data["image_files"]:
                try:
                    self.map_files_list = json.loads(session_data["image_files"])
                except:
                    self.map_files_list = []
            else:
                self.map_files_list = []

            # Update map listbox
            self.map_listbox.delete(0, tk.END)
            for filename in self.map_files_list:
                self.map_listbox.insert(tk.END, filename)

            if self.map_files_list:
                self.view_map_button.config(state=tk.NORMAL)
                self.delete_map_button.config(state=tk.NORMAL)
            else:
                self.view_map_button.config(state=tk.DISABLED)
                self.delete_map_button.config(state=tk.DISABLED)

            self.update_subjects_found()
            self.subjects_found_var.set(session_data["subjects_found"])
            self.update_subject_responses_grid()

            # Load selected terrains
            session_id = session_data["id"]
            self.accumulated_terrains = db_mgr.load_selected_terrains(session_id)
            self.accumulated_terrain_combo['values'] = self.accumulated_terrains
            # Enable combobox if terrains were loaded, disable if empty
            if self.accumulated_terrains:
                self.accumulated_terrain_combo['state'] = 'readonly'
            else:
                self.accumulated_terrain_combo['state'] = 'disabled'

            # Load subject responses
            subject_responses = db_mgr.load_subject_responses(session_id)
            for response in subject_responses:
                item_id = f'subject_{response["subject_number"]}'
                if self.subject_responses_tree.exists(item_id):
                    self.subject_responses_tree.item(
                        item_id,
                        values=(
                            f'Subject {response["subject_number"]}',
                            response["tfr"],
                            response["refind"]
                        )
                    )

            self.status_var.set(f"Loaded session #{session_number}")
        else:
            # Session doesn't exist - clear for new entry
            self.set_date(datetime.now().strftime("%Y-%m-%d"))
            self.purpose_var.set("")
            self.field_support_var.set("")
            self.location_var.set("")
            self.search_area_var.set("")
            self.num_subjects_var.set("")
            self.handler_knowledge_var.set("")
            self.weather_var.set("")
            self.temperature_var.set("")
            self.wind_direction_var.set("")
            self.wind_speed_var.set("")
            self.search_type_var.set("")
            self.drive_level_var.set("")
            self.subjects_found_var.set("")
            self.comments_text.delete("1.0", tk.END)
            self.accumulated_terrains = []
            self.accumulated_terrain_combo['values'] = []
            self.accumulated_terrain_var.set("")
            self.accumulated_terrain_combo['state'] = 'disabled'  # Disable when cleared
            self.map_files_list = []
            self.map_listbox.delete(0, tk.END)
            self.view_map_button.config(state=tk.DISABLED)
            self.delete_map_button.config(state=tk.DISABLED)
            self.update_subjects_found()
            self.status_var.set(f"New session #{session_number}")

    def update_navigation_buttons(self):
        """Enable/disable Previous and Next buttons based on current session number"""
        # If we have selected sessions, use that for navigation
        if self.selected_sessions:
            # Enable Previous if not at first selected session
            if self.selected_sessions_index > 0:
                self.prev_session_btn.config(state=tk.NORMAL)
            else:
                self.prev_session_btn.config(state=tk.DISABLED)
            
            # Enable Next if not at last selected session
            if self.selected_sessions_index < len(self.selected_sessions) - 1:
                self.next_session_btn.config(state=tk.NORMAL)
            else:
                self.next_session_btn.config(state=tk.DISABLED)
        else:
            # Normal mode - use session number
            try:
                current_session = int(self.session_var.get())
                max_session = self.get_next_session_number() - 1
                
                # Enable Previous if session > 1
                if current_session > 1:
                    self.prev_session_btn.config(state=tk.NORMAL)
                else:
                    self.prev_session_btn.config(state=tk.DISABLED)
                
                # Enable Next if session < max + 1
                if current_session < max_session + 1:
                    self.next_session_btn.config(state=tk.NORMAL)
                else:
                    self.next_session_btn.config(state=tk.DISABLED)
                    
            except ValueError:
                self.prev_session_btn.config(state=tk.DISABLED)
                self.next_session_btn.config(state=tk.DISABLED)
    
    def add_to_terrain_accumulator(self, event=None):
        """Add selected terrain type to the accumulated terrains list"""
        terrain_type = self.terrain_var.get()
        if terrain_type:
            # Check for duplicates
            if terrain_type in self.accumulated_terrains:
                messagebox.showinfo("Duplicate", f"'{terrain_type}' is already in the list")
                self.terrain_var.set("")
                return
            
            # Add to list
            self.accumulated_terrains.append(terrain_type)
            
            # Update combobox values
            self.accumulated_terrain_combo['values'] = self.accumulated_terrains
            
            # Enable the combobox if this is the first item
            if len(self.accumulated_terrains) == 1:
                self.accumulated_terrain_combo['state'] = 'readonly'
            
            # Display the last (newest) entry
            self.accumulated_terrain_var.set(terrain_type)
            
            # Clear selection in add terrain combobox
            self.terrain_var.set("")
    
    def remove_terrain_from_list(self, event):
        """Remove terrain type from list when clicked/selected"""
        terrain_type = self.accumulated_terrain_var.get()
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
            self.accumulated_terrain_combo['values'] = self.accumulated_terrains
            
            # Determine what to display after removal
            if len(self.accumulated_terrains) == 0:
                # List is now empty - show blank and disable combobox
                self.accumulated_terrain_var.set("")
                self.accumulated_terrain_combo['state'] = 'disabled'
            elif removed_index < len(self.accumulated_terrains):
                # Show the item that's now at the same index (the one that was below)
                self.accumulated_terrain_var.set(self.accumulated_terrains[removed_index])
            else:
                # The last item was removed - show the new last item
                self.accumulated_terrain_var.set(self.accumulated_terrains[-1])
    
    def update_subjects_found(self, event=None):
        """Update Subjects Found combobox values based on Number of Subjects"""
        num_subjects = self.num_subjects_var.get()
        
        if num_subjects and num_subjects.isdigit():
            n = int(num_subjects)
            # Generate values: "0 out of n", "1 out of n", ..., "n out of n"
            values = [f"{i} out of {n}" for i in range(n + 1)]
            self.subjects_found_combo['values'] = values
            self.subjects_found_combo['state'] = 'readonly'
            # Clear current selection when choices change
            self.subjects_found_var.set("")
        else:
            # No number selected, disable and clear the subjects_found combobox
            self.subjects_found_combo['values'] = []
            self.subjects_found_combo['state'] = 'disabled'
            self.subjects_found_var.set("")
        
        # Update TFR and Re-find state whenever subjects_found changes
        self.update_subject_responses_grid()
    
    def update_subject_responses_grid(self, event=None):
        """Update subject responses grid - enable/disable rows based on Subjects Found value"""
        subjects_found = self.subjects_found_var.get()
        
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
                self.subject_responses_tree.item(item_id, tags=(row_tag, 'enabled'))
            else:
                # Disable this row and clear values (keep odd/even tag for background shading)
                self.subject_responses_tree.item(item_id, values=(f'Subject {i}', '', ''), tags=(row_tag, 'disabled'))
    
    def on_treeview_click(self, event):
        """Handle click on treeview - show inline combobox for TFR/Re-find columns"""
        # Identify what was clicked
        region = self.subject_responses_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        
        item = self.subject_responses_tree.identify_row(event.y)
        column = self.subject_responses_tree.identify_column(event.x)
        
        if not item or not column:
            return
        
        # Check if row is enabled
        tags = self.subject_responses_tree.item(item, 'tags')
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
        x, y, width, height = self.subject_responses_tree.bbox(item, column)
        
        # Get current values
        values = list(self.subject_responses_tree.item(item, 'values'))
        current_value = values[col_index - 1] if col_index <= len(values) else ''
        
        # Determine options based on column
        if col_index == 2:  # TFR column
            options = self.tfr_options
        else:  # Re-find column
            options = self.refind_options
        
        # Create combobox positioned over the cell
        self.tree_edit_combo = ttk.Combobox(
            self.subject_responses_tree,
            values=options,
            state='readonly'
        )
        self.tree_edit_combo.set(current_value)
        
        # Position the combobox
        self.tree_edit_combo.place(x=x, y=y, width=width, height=height)
        
        # Store editing context
        self.tree_edit_item = item
        self.tree_edit_column = col_index
        
        # Bind events
        self.tree_edit_combo.bind('<<ComboboxSelected>>', self.on_tree_edit_select)
        self.tree_edit_combo.bind('<FocusOut>', lambda e: self.close_tree_edit())
        self.tree_edit_combo.bind('<Escape>', lambda e: self.close_tree_edit())
        
        # Focus and open dropdown
        self.tree_edit_combo.focus_set()
        self.tree_edit_combo.event_generate('<Button-1>')
    
    def on_tree_edit_select(self, event=None):
        """Handle selection in inline edit combobox"""
        if not self.tree_edit_combo or not self.tree_edit_item:
            return
        
        # Get the new value
        new_value = self.tree_edit_combo.get()
        
        # Update the treeview
        values = list(self.subject_responses_tree.item(self.tree_edit_item, 'values'))
        values[self.tree_edit_column - 1] = new_value
        self.subject_responses_tree.item(self.tree_edit_item, values=values)
        
        # Close the combobox
        self.close_tree_edit()
    
    def close_tree_edit(self):
        """Close the inline edit combobox"""
        if self.tree_edit_combo:
            self.tree_edit_combo.destroy()
            self.tree_edit_combo = None
        self.tree_edit_item = None
        self.tree_edit_column = None
    
    def reset_subject_responses_tree_selection(self):
        """Reset tree selection and scroll to subject 1"""
        if hasattr(self, 'subject_responses_tree'):
            # Clear any current selection
            self.subject_responses_tree.selection_remove(self.subject_responses_tree.selection())
            
            # Select subject 1 (first item)
            first_item = 'subject_1'
            if self.subject_responses_tree.exists(first_item):
                self.subject_responses_tree.selection_set(first_item)
                self.subject_responses_tree.see(first_item)  # Scroll to make it visible
    
    def drag_enter(self, event):
        """Visual feedback when dragging over drop zone"""
        self.drop_label.configure(bg="#90EE90")
    
    def drag_leave(self, event):
        """Reset visual feedback"""
        self.drop_label.configure(bg="#e0e0e0")
    
    def handle_drop(self, event):
        """Handle dropped files (supports multiple) - copies to trail maps folder"""
        self.drop_label.configure(bg="#e0e0e0")
        
        # Check if trail maps folder is configured
        trail_maps_folder = self.folder_path_var.get().strip()
        if not trail_maps_folder or not os.path.exists(trail_maps_folder):
            messagebox.showerror(
                "Trail Maps Folder Not Set",
                "Please configure the Trail Maps Storage Folder in the Setup tab first."
            )
            return
        
        # Check if dog is selected (needed for unique filename)
        if not hasattr(self, 'dog_var') or not self.dog_var.get():
            messagebox.showwarning(
                "No Dog Selected",
                "Please select a dog before adding maps/images.\n\n"
                "The dog name is used to organize files."
            )
            return
        
        dog_name = self.dog_var.get()
        session_number = self.session_var.get()
        
        # Parse dropped data - can be multiple files
        data = event.data.strip()
        
        # Split by whitespace but respect curly braces grouping
        filepaths = []
        if data.startswith("{"):
            # Multiple files with curly braces
            parts = data.split("} {")
            for part in parts:
                part = part.strip("{}")
                if part:
                    filepaths.append(part)
        else:
            # Single file or space-separated files
            filepaths = [data]
        
        # Process each file
        copied_files = []
        import shutil
        import re
        from datetime import datetime
        
        for filepath in filepaths:
            filepath = filepath.strip()
            if os.path.exists(filepath):
                ext = os.path.splitext(filepath)[1].lower()
                if ext in ['.pdf', '.jpg', '.jpeg', '.png']:
                    # Create unique filename: {dog}_{session}_{timestamp}_{original}
                    original_name = os.path.basename(filepath)
                    # Sanitize dog name for filename
                    safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    unique_name = f"{safe_dog_name}_session{session_number}_{timestamp}_{original_name}"
                    
                    # Copy file to trail maps folder
                    dest_path = os.path.join(trail_maps_folder, unique_name)
                    try:
                        shutil.copy2(filepath, dest_path)
                        copied_files.append(unique_name)  # Store just the filename, not full path
                    except Exception as e:
                        messagebox.showerror("Copy Error", f"Failed to copy {original_name}:\n{e}")
        
        if copied_files:
            # Add to list (don't replace, accumulate)
            self.map_files_list.extend(copied_files)
            # Remove duplicates while preserving order
            seen = set()
            self.map_files_list = [x for x in self.map_files_list if not (x in seen or seen.add(x))]
            
            # Update listbox
            self.map_listbox.delete(0, tk.END)
            for filename in self.map_files_list:
                self.map_listbox.insert(tk.END, filename)
            
            # Enable view and delete buttons
            self.view_map_button.config(state=tk.NORMAL)
            self.delete_map_button.config(state=tk.NORMAL)
            
            self.status_var.set(f"{len(copied_files)} file(s) copied to trail maps folder")
        else:
            messagebox.showerror("Error", "Only PDF, JPG, and PNG files supported!")
    
    
    def view_selected_map(self):
        """Open the selected map/image file from trail maps folder"""
        selection = self.map_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a file from the list to view")
            return
        
        # Get the filename from map_files_list using the index
        selected_index = selection[0]
        if selected_index < len(self.map_files_list):
            filename = self.map_files_list[selected_index]
            
            # Build full path from trail maps folder
            trail_maps_folder = self.folder_path_var.get().strip()
            if trail_maps_folder:
                filepath = os.path.join(trail_maps_folder, filename)
            else:
                filepath = filename
            
            self.open_external_file(filepath)
    
    def delete_selected_map(self):
        """Delete the selected map/image file from trail maps folder"""
        selection = self.map_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a file from the list to delete")
            return
        
        selected_index = selection[0]
        if selected_index >= len(self.map_files_list):
            return
        
        filename = self.map_files_list[selected_index]
        
        # Warning dialog
        result = messagebox.askokcancel(
            "Delete Map/Image",
            f"Are you sure you want to delete '{filename}'?\n\nThis operation cannot be reversed.",
            icon='warning'
        )
        
        if not result:
            return
        
        # Delete the actual file from trail maps folder
        try:
            trail_maps_folder = self.folder_path_var.get().strip()
            if trail_maps_folder:
                full_path = os.path.join(trail_maps_folder, filename)
            else:
                full_path = filename
            
            if os.path.exists(full_path):
                os.remove(full_path)
                self.status_var.set(f"Deleted file: {filename}")
            else:
                self.status_var.set(f"Removed from list (file not found): {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete file:\n{str(e)}")
            return
        
        # Remove from list and listbox
        self.map_files_list.pop(selected_index)
        self.map_listbox.delete(selected_index)
        
        # Update button states
        if not self.map_files_list:
            self.view_map_button.config(state=tk.DISABLED)
            self.delete_map_button.config(state=tk.DISABLED)
    
    def open_external_file(self, file_path):
        """Open a file (PDF, image, etc.) with the system's default application"""
        if not file_path or file_path == '':
            messagebox.showwarning("No File", "No file path specified")
            return
        
        # Convert to Path object
        path = Path(file_path)
        
        # If path is relative, try to find it in the trail maps folder
        if not path.is_absolute():
            possible_paths = []
            
            # Try trail maps folder from config first
            trail_maps_folder = self.folder_path_var.get()
            if trail_maps_folder and os.path.exists(trail_maps_folder):
                possible_paths.append(Path(trail_maps_folder) / file_path)
            
            # Try as-is
            possible_paths.append(path)
            
            # Find first existing path
            found_path = None
            for p in possible_paths:
                if p.exists():
                    found_path = p
                    break
            
            if found_path:
                path = found_path
            else:
                error_msg = f"Could not find file: {file_path}\n\nSearched in:\n"
                for p in possible_paths:
                    error_msg += f"  • {p}\n"
                error_msg += "\nTip: Check your trail maps folder setting in Setup tab."
                messagebox.showerror("File Not Found", error_msg)
                return
        
        if not path.exists():
            messagebox.showerror("File Not Found", f"Could not find file:\n{path}")
            return
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS or Linux
                import subprocess
                import platform
                if platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', path])
                else:  # Linux
                    subprocess.run(['xdg-open', path])
        except Exception as e:
            messagebox.showerror("Error Opening File", 
                               f"Could not open file:\n{path}\n\nError: {str(e)}")
    
    def load_prior_session(self):
        """Open dialog to select sessions to view/edit/delete for current dog"""
        db_type = self.db_type_var.get()
        
        # Check if dog_var exists
        if not hasattr(self, 'dog_var'):
            messagebox.showwarning("Initialization Error", "UI not fully initialized")
            return
        
        dog_name = self.dog_var.get()
        
        # Check if dog is selected
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first to view their sessions")
            return
        
        try:
            # Get all sessions from database for this dog
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            from sqlalchemy import text
            
            # Show working dialog for networked databases
            if db_type in ["postgres", "supabase", "mysql"]:
                working_dialog = WorkingDialog(self.root, "Loading", 
                                             f"Loading session list from {db_type} database...")
                self.root.update()
            else:
                working_dialog = None
            
            try:
                with database.get_connection() as conn:
                    result = conn.execute(
                        text("""
                            SELECT session_number, date, handler, dog_name
                            FROM training_sessions 
                            WHERE dog_name = :dog_name
                            ORDER BY session_number
                        """),
                        {"dog_name": dog_name}
                    )
                    sessions = result.fetchall()
            finally:
                if working_dialog:
                    working_dialog.close(delay_ms=200)
            
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            if not sessions:
                messagebox.showinfo("No Sessions", f"No training sessions found for {dog_name}.")
                return
            
            # Create selection dialog
            self.show_session_selection_dialog(sessions)
            
        except Exception as e:
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
                messagebox.showinfo("No Database", "No training sessions table found. Create database first.")
            else:
                messagebox.showerror("Database Error", f"Failed to load sessions:\n{e}")
                print(f"Error loading sessions: {e}")
    
    def show_session_selection_dialog(self, sessions):
        """Show dialog for selecting sessions to view/edit"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Sessions to View/Edit/Delete")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        
        # Instructions
        instructions = tk.Label(
            dialog, 
            text="Select sessions to navigate:\n"
                 "• Click to select one session\n"
                 "• Ctrl+Click to select multiple sessions\n"
                 "• Shift+Click to select a range\n"
                 "Use Previous/Next buttons to navigate through selected sessions",
            justify=tk.LEFT,
            padx=10,
            pady=10
        )
        instructions.pack()
        
        # Listbox with scrollbar
        frame = tk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(
            frame, 
            selectmode=tk.EXTENDED,  # Allow Ctrl+Click and Shift+Click
            yscrollcommand=scrollbar.set,
            font=("Courier", 10)
        )
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Populate listbox
        for session in sessions:
            session_num, date, handler, dog = session
            handler = handler or ""
            dog = dog or ""
            text = f"Session #{session_num:3d}  |  {date}  |  {handler:20s}  |  {dog}"
            listbox.insert(tk.END, text)
        
        # Store session numbers for reference
        session_numbers = [s[0] for s in sessions]
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_view_selected():
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            # Get selected session numbers
            self.selected_sessions = [session_numbers[i] for i in selected_indices]
            self.selected_sessions_index = 0
            
            # Load the first selected session
            self.session_var.set(str(self.selected_sessions[0]))
            self.load_session_by_number(self.selected_sessions[0])
            self.update_navigation_buttons()
            
            dialog.destroy()
            self.status_var.set(f"Viewing {len(self.selected_sessions)} selected sessions")
        
        def on_delete_selected():
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session to delete")
                return
            
            selected_nums = [session_numbers[i] for i in selected_indices]
            result = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete {len(selected_nums)} session(s)?\n\n"
                f"Sessions: {', '.join(map(str, selected_nums))}\n\n"
                "This action cannot be undone!",
                icon='warning'
            )
            
            if result:
                self.delete_sessions(selected_nums)
                dialog.destroy()
        
        tk.Button(button_frame, text="View Selected", command=on_view_selected,
                 bg="#4169E1", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(button_frame, text="Delete Selected", command=on_delete_selected,
                 bg="#DC143C", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 width=10).pack(side="left", padx=5)
    
    def delete_sessions(self, session_numbers):
        """Delete multiple sessions for current dog"""
        if not hasattr(self, 'dog_var'):
            messagebox.showerror("Error", "UI not fully initialized")
            return
        
        dog_name = self.dog_var.get()
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.delete_sessions(session_numbers, dog_name)
        
        if success:
            messagebox.showinfo("Success", message)
            self.selected_sessions = []
            self.selected_sessions_index = -1
            self.new_session()
        else:
            messagebox.showerror("Database Error", message)
    
    def navigate_previous_session(self):
        """Navigate to previous session"""
        # If we have selected sessions, navigate through those
        if self.selected_sessions and self.selected_sessions_index > 0:
            self.selected_sessions_index -= 1
            session_num = self.selected_sessions[self.selected_sessions_index]
            self.session_var.set(str(session_num))
            self.load_session_by_number(session_num)
            self.reset_subject_responses_tree_selection()  # Reset to subject 1
            self.update_navigation_buttons()
            self.status_var.set(
                f"Session {self.selected_sessions_index + 1} of {len(self.selected_sessions)} selected"
            )
        else:
            # Normal navigation - just decrement
            try:
                current = int(self.session_var.get())
                if current > 1:
                    self.session_var.set(str(current - 1))
                    self.load_session_by_number(current - 1)
                    self.reset_subject_responses_tree_selection()  # Reset to subject 1
                    self.update_navigation_buttons()
            except ValueError:
                pass
    
    def navigate_next_session(self):
        """Navigate to next session"""
        # If we have selected sessions, navigate through those
        if self.selected_sessions and self.selected_sessions_index < len(self.selected_sessions) - 1:
            self.selected_sessions_index += 1
            session_num = self.selected_sessions[self.selected_sessions_index]
            self.session_var.set(str(session_num))
            self.load_session_by_number(session_num)
            self.reset_subject_responses_tree_selection()  # Reset to subject 1
            self.update_navigation_buttons()
            self.status_var.set(
                f"Session {self.selected_sessions_index + 1} of {len(self.selected_sessions)} selected"
            )
        else:
            # Normal navigation - just increment
            try:
                current = int(self.session_var.get())
                max_session = self.get_next_session_number() - 1
                if current < max_session + 1:
                    self.session_var.set(str(current + 1))
                    self.load_session_by_number(current + 1)
                    self.reset_subject_responses_tree_selection()  # Reset to subject 1
                    self.update_navigation_buttons()
            except ValueError:
                pass
    
    def open_export_dialog(self):
        """Open export PDF dialog"""
        # Check if dog is selected
        if not hasattr(self, 'dog_var') or not self.dog_var.get():
            messagebox.showwarning("No Dog Selected", "Please select a dog before exporting")
            return
        
        # Check if trail maps folder is configured
        trail_maps_folder = self.folder_path_var.get().strip()
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
            db_type=self.db_type_var.get(),
            current_dog=self.dog_var.get(),
            get_connection_func=get_connection,
            backup_folder=self.backup_path_var.get().strip(),
            trail_maps_folder=trail_maps_folder
        )
    
    # File/Folder selection methods
    def select_db_folder(self):
        """Select database folder"""
        folder = filedialog.askdirectory(title="Select Database Folder")
        if folder:
            self.db_path_var.set(folder)
            self.machine_db_path = folder
    
    def select_folder(self):
        """Select trail maps folder"""
        folder = filedialog.askdirectory(title="Select Trail Maps Storage Folder")
        if folder:
            self.folder_path_var.set(folder)
            self.machine_trail_maps_folder = folder
    
    def select_backup_folder(self):
        """Select backup folder"""
        folder = filedialog.askdirectory(title="Select Backup Folder")
        if folder:
            self.backup_path_var.set(folder)
            self.machine_backup_folder = folder
    
    def update_create_db_button_state(self, *args):
        """Enable/disable Create Database button based on folder selection and database type"""
        db_type = self.db_type_var.get()
        has_folder = bool(self.db_path_var.get().strip())
        
        # For SQLite, require folder. For postgres/supabase/mysql, always enable
        if db_type == "sqlite":
            self.create_db_btn.config(state="normal" if has_folder else "disabled")
        else:  # postgres, supabase, or mysql
            self.create_db_btn.config(state="normal")
    
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
        db_type = self.db_type_var.get()
        
        # Show password field for postgres, supabase, mysql
        # Hide for sqlite
        if db_type in ["postgres", "supabase", "mysql"]:
            self.db_password_frame.pack(pady=5)
            
            # Try to load saved encrypted password for this database type
            from password_manager import get_decrypted_password, check_crypto_available
            
            if check_crypto_available():
                saved_password = get_decrypted_password(self.config, db_type)
                if saved_password:
                    self.db_password_var.set(saved_password)
                    # CRITICAL FIX: Actually set the password in the database configuration
                    # Without this, the password shows in the field but isn't used for connection
                    self.set_db_password()
                    # Only update status if status_var exists (may not during initialization)
                    if hasattr(self, 'status_var'):
                        self.status_var.set(f"Loaded saved password for {db_type}")
                else:
                    self.db_password_var.set("")
            else:
                self.db_password_var.set("")
        else:
            self.db_password_frame.pack_forget()
    
    def toggle_password_visibility(self):
        """Toggle password visibility in entry field"""
        if self.show_password_var.get():
            self.db_password_entry.config(show="")
        else:
            self.db_password_entry.config(show="*")
    
    def set_db_password(self):
        """Set database password in config at runtime and optionally save encrypted"""
        import config
        
        db_type = self.db_type_var.get()
        password = self.db_password_var.get()
        
        if db_type in ["postgres", "supabase", "mysql"] and password:
            # Set the password in config
            config.DB_PASSWORD = password
            
            # Build the connection URL with password
            url_template = config.DB_CONFIG[db_type].get("url_template", "")
            if url_template:
                config.DB_CONFIG[db_type]["url"] = url_template.format(password=password)
            
            # Save encrypted password if "Remember" is checked
            # Check if remember_password_var exists (may not during initialization)
            if hasattr(self, 'remember_password_var') and self.remember_password_var.get():
                from password_manager import save_encrypted_password, check_crypto_available
                
                if check_crypto_available():
                    if save_encrypted_password(self.config, db_type, password):
                        self.save_config()
                        # Only update status if status_var exists (may not during initialization)
                        if hasattr(self, 'status_var'):
                            self.status_var.set(f"Password saved (encrypted) for {db_type}")
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
        db_type = self.db_type_var.get()
        
        if db_type not in ["postgres", "supabase", "mysql"]:
            return
        
        from password_manager import clear_saved_password
        
        # Clear from config
        clear_saved_password(self.config, db_type)
        self.save_config()
        
        # Clear from UI
        self.db_password_var.set("")
        
        self.status_var.set(f"Forgot saved password for {db_type}")
        messagebox.showinfo("Password Cleared", f"Saved password for {db_type} has been cleared.")
    
    def prepare_db_connection(self, db_type):
        """Prepare database connection by setting password if needed"""
        if db_type in ["postgres", "supabase", "mysql"]:
            password = self.db_password_var.get().strip()
            if not password:
                messagebox.showerror(
                    "Password Required",
                    f"Please enter the database password for {db_type} in the Setup tab."
                )
                return False
            
            # Update the password
            self.db_password_var.set(password)
            self.set_db_password()
        
        return True
    
    def create_database(self):
        """Create or rebuild database schema"""
        from pathlib import Path
        
        # Get selected database type
        db_type = self.db_type_var.get()
        
        if db_type == "sqlite":
            # SQLite requires a folder
            folder = self.db_path_var.get().strip()
            if not folder:
                messagebox.showwarning("No Folder", "Please select a database folder first")
                return
            
            # Check if folder exists
            folder_path = Path(folder)
            if not folder_path.exists():
                messagebox.showerror("Invalid Folder", f"Folder does not exist:\n{folder}")
                return
            
            db_path = folder_path / "air_scenting.db"
            db_exists = db_path.exists()
            
            if db_exists:
                result = messagebox.askyesno(
                    "Database Exists",
                    f"A database already exists at:\n{db_path}\n\n"
                    "Do you want to rebuild it?\n\n"
                    "WARNING: This will delete all existing data!",
                    icon='warning'
                )
                if not result:
                    return
                
                # Close any existing database connections
                try:
                    from database import engine
                    engine.dispose()
                    self.status_var.set("Closed database connections...")
                except Exception as e:
                    print(f"Note: Could not dispose engine: {e}")
                
                # Delete existing database
                try:
                    db_path.unlink()
                except PermissionError:
                    messagebox.showerror(
                        "Database In Use",
                        f"Cannot delete database - it may be in use by another program.\n\n"
                        f"Please close any programs using the database and try again.\n\n"
                        f"Database: {db_path}"
                    )
                    return
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete existing database:\n{e}")
                    return
            
            # Create new SQLite database with schema
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                conn.close()
                
                # Update config.py temporarily for schema creation
                import config
                old_db_type = config.DB_TYPE
                old_db_url = config.DB_CONFIG[old_db_type]["url"]
                
                # Temporarily point to the new database
                config.DB_TYPE = "sqlite"
                config.DB_CONFIG["sqlite"]["url"] = f"sqlite:///{db_path}"
                
                # Recreate engine with new database
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                # Create schema
                from schema import create_tables
                create_tables()
                
                # Restore original config
                config.DB_TYPE = old_db_type
                config.DB_CONFIG[old_db_type]["url"] = old_db_url
                database.engine.dispose()
                reload(database)
                
                self.status_var.set(f"Database created: {db_path}")
                messagebox.showinfo(
                    "Success", 
                    f"SQLite database created successfully!\n\n{db_path}\n\n"
                    f"Schema initialized with training_sessions table."
                )
                
                # Offer to restore from JSON backups
                self.restore_from_json_backups("sqlite")
                
                # Offer to load default terrain and distraction types
                self.offer_load_default_types("sqlite")
                
                # Update session number and UI after database recreation
                self.session_var.set(str(self.get_next_session_number()))
                self.selected_sessions = []
                self.selected_sessions_index = -1
                self.update_navigation_buttons()
                # Clear form to new entry state
                self.set_date(datetime.now().strftime("%Y-%m-%d"))
                self.purpose_var.set("")
                self.field_support_var.set("")
                self.dog_var.set("")
                self.search_area_var.set("")
                self.num_subjects_var.set("")
                self.handler_knowledge_var.set("")
                self.weather_var.set("")
                self.temperature_var.set("")
                self.wind_direction_var.set("")
                self.wind_speed_var.set("")
                self.search_type_var.set("")
                self.drive_level_var.set("")
                self.subjects_found_var.set("")
                # Update subjects_found combo state (will disable since num_subjects is blank)
                self.update_subjects_found()
                
                # Refresh dog list on Setup tab (new database has no dogs)
                self.refresh_dog_list()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create database:\n{e}\n\n{type(e).__name__}")
                import traceback
                traceback.print_exc()
        
        else:  # postgres, supabase, or mysql
            # Check if password has been entered
            password = self.db_password_var.get().strip()
            if not password:
                messagebox.showerror(
                    "Password Required",
                    f"Please enter the database password for {db_type}."
                )
                return
            
            # Set the password in config at runtime
            self.set_db_password()
            
            # For PostgreSQL/Supabase/MySQL, check if tables exist and offer to rebuild
            try:
                # Temporarily switch to the selected database type
                import config
                old_db_type = config.DB_TYPE
                
                config.DB_TYPE = db_type
                
                # Reload database module with new DB_TYPE
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from schema import create_tables, drop_tables
                from sqlalchemy import text
                
                # Show working dialog while checking connection
                working_dialog = WorkingDialog(self.root, "Connecting", 
                                             f"Connecting to {db_type} database...")
                self.root.update()
                
                # Check if training_sessions table exists
                try:
                    with database.get_connection() as conn:
                        check_query = text("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'training_sessions'
                            )
                        """)
                        
                        result = conn.execute(check_query)
                        table_exists = result.scalar()
                finally:
                    working_dialog.close(delay_ms=200)
                
                if table_exists:
                    result = messagebox.askyesno(
                        "Database Tables Exist",
                        f"Tables already exist in the {db_type} database.\n\n"
                        "Do you want to rebuild them?\n\n"
                        "WARNING: This will delete all existing data!",
                        icon='warning'
                    )
                    if not result:
                        # Restore original DB_TYPE
                        config.DB_TYPE = old_db_type
                        database.engine.dispose()
                        reload(database)
                        return
                    
                    # Drop existing tables
                    working_dialog = WorkingDialog(self.root, "Deleting", 
                                                 f"Deleting existing {db_type} tables...")
                    self.root.update()
                    try:
                        drop_tables()
                        self.status_var.set("Dropped existing tables...")
                    finally:
                        working_dialog.close(delay_ms=200)
                
                # Create tables
                working_dialog = WorkingDialog(self.root, "Creating Database", 
                                             f"Creating {db_type} database schema...")
                self.root.update()
                try:
                    create_tables()
                finally:
                    working_dialog.close(delay_ms=200)
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                self.status_var.set(f"{db_type.title()} schema created successfully")
                messagebox.showinfo(
                    "Success",
                    f"{db_type.title()} database schema created successfully!\n\n"
                    f"Tables initialized:\n"
                    f"  - training_sessions"
                )
                
                # Offer to restore from JSON backups
                self.restore_from_json_backups(db_type)
                
                # Offer to load default terrain and distraction types
                self.offer_load_default_types(db_type)
                
                # Update session number and UI after database recreation
                self.session_var.set(str(self.get_next_session_number()))
                self.selected_sessions = []
                self.selected_sessions_index = -1
                self.update_navigation_buttons()
                # Clear form to new entry state
                self.set_date(datetime.now().strftime("%Y-%m-%d"))
                self.purpose_var.set("")
                self.field_support_var.set("")
                self.dog_var.set("")
                self.search_area_var.set("")
                self.num_subjects_var.set("")
                self.handler_knowledge_var.set("")
                self.weather_var.set("")
                self.temperature_var.set("")
                self.wind_direction_var.set("")
                self.wind_speed_var.set("")
                self.search_type_var.set("")
                self.drive_level_var.set("")
                self.subjects_found_var.set("")
                # Update subjects_found combo state (will disable since num_subjects is blank)
                self.update_subjects_found()
                
                # Refresh dog list on Setup tab (new database has no dogs)
                self.refresh_dog_list()
                
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
                
                messagebox.showerror(
                    "Database Error",
                    f"Failed to create {db_type} database schema:\n\n{e}\n\n{type(e).__name__}\n\n"
                    f"Make sure:\n"
                    f"1. Database password is correct\n"
                    f"2. Database server is accessible\n"
                    f"3. You have proper credentials and permissions\n"
                    f"4. Connection string in config.py is correct"
                )
                import traceback
                traceback.print_exc()
    
    # Training Locations methods
    def load_locations_from_database(self):
        """Load training locations from database into Setup tab listbox"""
        # Ensure database is ready (critical for networked databases)
        self.ensure_db_ready()
        
        db_mgr = get_db_manager(self.db_type_var.get())
        locations = db_mgr.load_locations()
        
        # Update UI
        self.location_listbox.delete(0, tk.END)
        for location in locations:
            self.location_listbox.insert(tk.END, location)
    
    def refresh_location_list(self):
        """Refresh the location combobox in Entry tab"""
        db_mgr = get_db_manager(self.db_type_var.get())
        locations = db_mgr.load_locations()
        
        # Update combobox
        if hasattr(self, 'location_combo'):
            self.location_combo['values'] = locations
    
    def refresh_terrain_list(self):
        """Refresh the terrain type combobox in Entry tab"""
        # Use DatabaseManager to get terrain types in correct order (by sort_order)
        from ui_database import get_db_manager
        db_mgr = get_db_manager(self.db_type_var.get())
        terrain_types = db_mgr.load_terrain_types()
        
        # Update combobox
        if hasattr(self, 'terrain_combo'):
            self.terrain_combo['values'] = terrain_types
    
    def load_terrain_from_database(self):
        """Load terrain types from database into Setup tab treeview"""
        # Ensure database is ready (critical for networked databases)
        self.ensure_db_ready()
        
        db_mgr = get_db_manager(self.db_type_var.get())
        terrain_types = db_mgr.load_terrain_types()
        
        # Clear and populate treeview
        self.terrain_tree.delete(*self.terrain_tree.get_children())
        for idx, terrain in enumerate(terrain_types, 1):
            self.terrain_tree.insert('', tk.END, text=str(idx), values=(terrain,))
    
    def load_distraction_from_database(self):
        """Load distraction types from database into Setup tab treeview"""
        # Ensure database is ready (critical for networked databases)
        self.ensure_db_ready()
        
        db_mgr = get_db_manager(self.db_type_var.get())
        distraction_types = db_mgr.load_distraction_types()
        
        # Clear and populate treeview
        self.distraction_type_tree.delete(*self.distraction_type_tree.get_children())
        for idx, distraction in enumerate(distraction_types, 1):
            self.distraction_type_tree.insert('', tk.END, text=str(idx), values=(distraction,))
    
    def update_location_button_states(self, *args):
        """Enable/disable location buttons based on entry content"""
        has_text = bool(self.new_location_var.get().strip())
        self.add_location_btn.config(state="normal" if has_text else "disabled")
    
    def on_location_select(self, event):
        """Handle location selection in listbox"""
        selection = self.location_listbox.curselection()
        self.remove_location_btn.config(state="normal" if selection else "disabled")
    
    def add_location(self):
        """Add a new training location"""
        location = self.new_location_var.get().strip()
        if not location:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        db_type = self.db_type_var.get()
        
        # Show working dialog for networked databases
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.root, "Adding Location", 
                                         f"Adding location to {db_type} database...")
            self.root.update()
        else:
            working_dialog = None
        
        try:
            success, message = db_mgr.add_location(location)
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
        
        if success:
            self.load_locations_from_database()
            self.refresh_location_list()
            self.new_location_var.set("")
            self.status_var.set(message)
        else:
            if "already exists" in message:
                messagebox.showinfo("Duplicate", message)
            else:
                messagebox.showerror("Database Error", message)
    
    def remove_location(self):
        """Remove selected training location"""
        selection = self.location_listbox.curselection()
        if not selection:
            return
        
        location = self.location_listbox.get(selection[0])
        
        result = messagebox.askyesno("Confirm Delete", 
                                     f"Delete location '{location}'?")
        if not result:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.remove_location(location)
        
        if success:
            self.load_locations_from_database()
            self.refresh_location_list()
            self.status_var.set(message)
            self.remove_location_btn.config(state="disabled")
        else:
            messagebox.showerror("Database Error", message)
    
    def load_dogs_from_database(self):
        """Load dog names from database into listbox"""
        # Ensure database is ready (critical for networked databases)
        self.ensure_db_ready()
        
        db_mgr = get_db_manager(self.db_type_var.get())
        dogs = db_mgr.load_dogs()
        
        # Update UI
        self.dog_listbox.delete(0, tk.END)
        for dog in dogs:
            self.dog_listbox.insert(tk.END, dog)
    
    def refresh_dog_list(self):
        """Refresh the dog combobox in Entry tab"""
        db_mgr = get_db_manager(self.db_type_var.get())
        dogs = db_mgr.load_dogs()
        
        # Update combobox
        if hasattr(self, 'dog_combo'):
            self.dog_combo['values'] = dogs
        
        # Also update Setup tab listbox
        self.dog_listbox.delete(0, tk.END)
        for dog in dogs:
            self.dog_listbox.insert(tk.END, dog)
    
    def update_dog_button_states(self, *args):
        """Enable/disable dog buttons based on entry content"""
        has_text = bool(self.new_dog_var.get().strip())
        self.add_dog_btn.config(state="normal" if has_text else "disabled")
    
    def on_dog_select(self, event):
        """Handle dog selection in listbox"""
        selection = self.dog_listbox.curselection()
        self.remove_dog_btn.config(state="normal" if selection else "disabled")
    
    def add_dog(self):
        """Add a new dog"""
        dog_name = self.new_dog_var.get().strip()
        if not dog_name:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        db_type = self.db_type_var.get()
        
        # Show working dialog for networked databases
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.root, "Adding Dog", 
                                         f"Adding dog to {db_type} database...")
            self.root.update()
        else:
            working_dialog = None
        
        try:
            success, message = db_mgr.add_dog(dog_name)
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
        
        if success:
            self.load_dogs_from_database()
            if hasattr(self, 'dog_combo'):
                self.refresh_dog_list()
            self.new_dog_var.set("")
            self.status_var.set(message)
        else:
            if "already exists" in message:
                messagebox.showinfo("Duplicate", message)
            else:
                messagebox.showerror("Database Error", message)
    
    def remove_dog(self):
        """Remove selected dog"""
        selection = self.dog_listbox.curselection()
        if not selection:
            return
        
        dog_name = self.dog_listbox.get(selection[0])
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete dog '{dog_name}'?\n\n"
            "This will not delete training sessions for this dog."
        )
        if not result:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.remove_dog(dog_name)
        
        if success:
            self.dog_listbox.delete(selection[0])
            if hasattr(self, 'dog_combo'):
                self.refresh_dog_list()
            self.status_var.set(message)
            self.remove_dog_btn.config(state="disabled")
        else:
            messagebox.showerror("Database Error", message)
    
    # Terrain Types methods
    def update_terrain_button_states(self, *args):
        """Enable/disable terrain buttons based on entry content and selection"""
        has_text = bool(self.new_terrain_var.get().strip())
        self.add_terrain_btn.config(state="normal" if has_text else "disabled")
    
    def on_terrain_select(self, event):
        """Handle terrain type selection"""
        selection = self.terrain_tree.selection()
        has_selection = bool(selection)
        self.remove_terrain_btn.config(state="normal" if has_selection else "disabled")
        self.move_terrain_up_btn.config(state="normal" if has_selection else "disabled")
        self.move_terrain_down_btn.config(state="normal" if has_selection else "disabled")
    
    def add_terrain_type(self):
        """Add a new terrain type"""
        terrain = self.new_terrain_var.get().strip()
        if not terrain:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        db_type = self.db_type_var.get()
        
        # Show working dialog for networked databases
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.root, "Adding Terrain", 
                                         f"Adding terrain type to {db_type} database...")
            self.root.update()
        else:
            working_dialog = None
        
        try:
            success, message = db_mgr.add_terrain_type(terrain)
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
        
        if success:
            self.load_terrain_from_database()
            # Also refresh Entry tab terrain combobox
            if hasattr(self, 'terrain_combo'):
                self.refresh_terrain_list()
            self.new_terrain_var.set("")
            self.status_var.set(message)
        else:
            if "already exists" in message:
                messagebox.showinfo("Duplicate", message)
            else:
                messagebox.showerror("Database Error", message)
    
    def remove_terrain_type(self):
        """Remove selected terrain type"""
        selection = self.terrain_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.terrain_tree.item(item, 'values')
        terrain = values[0]
        
        result = messagebox.askyesno("Confirm Delete", 
                                    f"Delete terrain type '{terrain}'?")
        if not result:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.remove_terrain_type(terrain)
        
        if success:
            self.load_terrain_from_database()
            # Also refresh Entry tab terrain combobox
            if hasattr(self, 'terrain_combo'):
                self.refresh_terrain_list()
            self.status_var.set(message)
        else:
            messagebox.showerror("Database Error", message)
    
    def move_terrain_up(self):
        """Move selected terrain type up"""
        selection = self.terrain_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.terrain_tree.item(item, 'values')
        terrain = values[0]
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.move_terrain_up(terrain)
        
        if success:
            # Reload and reselect
            self.load_terrain_from_database()
            # Also refresh Entry tab terrain combobox
            if hasattr(self, 'terrain_combo'):
                self.refresh_terrain_list()
            # Find and select the moved item
            for child in self.terrain_tree.get_children():
                if self.terrain_tree.item(child, 'values')[0] == terrain:
                    self.terrain_tree.selection_set(child)
                    self.terrain_tree.see(child)
                    break
            self.status_var.set(message)
        else:
            if "Already at top" not in message:
                messagebox.showinfo("Cannot Move", message)
    
    def move_terrain_down(self):
        """Move selected terrain type down"""
        selection = self.terrain_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.terrain_tree.item(item, 'values')
        terrain = values[0]
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.move_terrain_down(terrain)
        
        if success:
            # Reload and reselect
            self.load_terrain_from_database()
            # Also refresh Entry tab terrain combobox
            if hasattr(self, 'terrain_combo'):
                self.refresh_terrain_list()
            # Find and select the moved item
            for child in self.terrain_tree.get_children():
                if self.terrain_tree.item(child, 'values')[0] == terrain:
                    self.terrain_tree.selection_set(child)
                    self.terrain_tree.see(child)
                    break
            self.status_var.set(message)
        else:
            if "Already at bottom" not in message:
                messagebox.showinfo("Cannot Move", message)
    
    def restore_default_terrain_types(self):
        """Restore default terrain types"""
        result = messagebox.askyesno(
            "Restore Defaults",
            "This will DELETE all existing terrain types and restore the default list.\n\n"
            "Are you sure you want to continue?"
        )
        if not result:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.restore_default_terrain_types()
        
        if success:
            self.load_terrain_from_database()
            # Also refresh Entry tab terrain combobox
            if hasattr(self, 'terrain_combo'):
                self.refresh_terrain_list()
            self.status_var.set(message)
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
    
    # Distraction Types methods
    def update_distraction_type_button_states(self, *args):
        """Enable/disable distraction type buttons"""
        has_text = bool(self.new_distraction_var.get().strip())
        self.add_distraction_type_btn.config(state="normal" if has_text else "disabled")
    
    def on_distraction_type_select(self, event):
        """Handle distraction type selection"""
        selection = self.distraction_type_tree.selection()
        has_selection = bool(selection)
        self.remove_distraction_type_btn.config(state="normal" if has_selection else "disabled")
        self.move_distraction_type_up_btn.config(state="normal" if has_selection else "disabled")
        self.move_distraction_type_down_btn.config(state="normal" if has_selection else "disabled")
    
    def add_distraction_type(self):
        """Add a new distraction type"""
        distraction = self.new_distraction_var.get().strip()
        if not distraction:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        db_type = self.db_type_var.get()
        
        # Show working dialog for networked databases
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.root, "Adding Distraction", 
                                         f"Adding distraction type to {db_type} database...")
            self.root.update()
        else:
            working_dialog = None
        
        try:
            success, message = db_mgr.add_distraction_type(distraction)
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
        
        if success:
            self.load_distraction_from_database()
            self.new_distraction_var.set("")
            self.status_var.set(message)
        else:
            if "already exists" in message:
                messagebox.showinfo("Duplicate", message)
            else:
                messagebox.showerror("Database Error", message)
    
    def remove_distraction_type(self):
        """Remove selected distraction type"""
        selection = self.distraction_type_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.distraction_type_tree.item(item, 'values')
        distraction = values[0]
        
        result = messagebox.askyesno("Confirm Delete", 
                                    f"Delete distraction type '{distraction}'?")
        if not result:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.remove_distraction_type(distraction)
        
        if success:
            self.load_distraction_from_database()
            self.status_var.set(message)
        else:
            messagebox.showerror("Database Error", message)
    
    def move_distraction_up(self):
        """Move selected distraction type up"""
        selection = self.distraction_type_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.distraction_type_tree.item(item, 'values')
        distraction = values[0]
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.move_distraction_up(distraction)
        
        if success:
            # Reload and reselect
            self.load_distraction_from_database()
            # Find and select the moved item
            for child in self.distraction_type_tree.get_children():
                if self.distraction_type_tree.item(child, 'values')[0] == distraction:
                    self.distraction_type_tree.selection_set(child)
                    self.distraction_type_tree.see(child)
                    break
            self.status_var.set(message)
        else:
            if "Already at top" not in message:
                messagebox.showinfo("Cannot Move", message)
    
    def move_distraction_down(self):
        """Move selected distraction type down"""
        selection = self.distraction_type_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.distraction_type_tree.item(item, 'values')
        distraction = values[0]
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.move_distraction_down(distraction)
        
        if success:
            # Reload and reselect
            self.load_distraction_from_database()
            # Find and select the moved item
            for child in self.distraction_type_tree.get_children():
                if self.distraction_type_tree.item(child, 'values')[0] == distraction:
                    self.distraction_type_tree.selection_set(child)
                    self.distraction_type_tree.see(child)
                    break
            self.status_var.set(message)
        else:
            if "Already at bottom" not in message:
                messagebox.showinfo("Cannot Move", message)
    
    def restore_default_distraction_types(self):
        """Restore default distraction types"""
        result = messagebox.askyesno(
            "Restore Defaults",
            "This will DELETE all existing distraction types and restore the default list.\n\n"
            "Are you sure you want to continue?"
        )
        if not result:
            return
        
        db_mgr = get_db_manager(self.db_type_var.get())
        success, message = db_mgr.restore_default_distraction_types()
        
        if success:
            self.load_distraction_from_database()
            self.status_var.set(message)
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
    
    # Configuration management
    def save_configuration_settings(self):
        """Save all configuration settings"""
        # Check for text in entry fields that hasn't been added
        unadded_items = []
        if self.new_location_var.get().strip():
            unadded_items.append(f"Location: '{self.new_location_var.get().strip()}'")
        if self.new_dog_var.get().strip():
            unadded_items.append(f"Dog: '{self.new_dog_var.get().strip()}'")
        if self.new_terrain_var.get().strip():
            unadded_items.append(f"Terrain: '{self.new_terrain_var.get().strip()}'")
        if self.new_distraction_var.get().strip():
            unadded_items.append(f"Distraction: '{self.new_distraction_var.get().strip()}'")
        
        if unadded_items:
            message = "You have typed text that hasn't been added:\n\n" + "\n".join(unadded_items)
            message += "\n\nDo you want to save anyway?\n(This text will be lost)"
            result = messagebox.askyesno("Unadded Items", message, icon='warning')
            if not result:
                return  # User cancelled
        
        # Update config with default values
        self.config["handler_name"] = self.default_handler_var.get()
        self.config["db_type"] = self.db_type_var.get()
        
        # Save config file
        self.save_config()
        
        # Save machine-specific paths
        self.machine_db_path = self.db_path_var.get()
        self.machine_trail_maps_folder = self.folder_path_var.get()
        self.machine_backup_folder = self.backup_path_var.get()
        self.save_bootstrap()
        
        # Save settings backup JSON file
        self.save_settings_backup()
        
        # Take new snapshot after saving
        self.take_form_snapshot()
        
        self.status_var.set("Configuration saved successfully!")
        messagebox.showinfo("Success", "Configuration saved successfully!")
    
    def get_form_state_string(self):
        """Get a string representation of all form fields for comparison"""
        parts = [
            self.db_type_var.get(),
            self.db_path_var.get(),
            self.folder_path_var.get(),
            self.backup_path_var.get(),
            self.default_handler_var.get(),
            # Include entry widget values (in case user typed but didn't click Add)
            self.new_location_var.get(),
            self.new_dog_var.get(),
            self.new_terrain_var.get(),
            self.new_distraction_var.get()
            # Note: Dogs, locations, terrain, and distraction types are stored in the database
            # and are saved immediately when added, so they don't need to be in this check
        ]
        return "|".join(parts)
    
    def take_form_snapshot(self):
        """Take a snapshot of the current form state"""
        self.form_snapshot = self.get_form_state_string()
    
    def has_unsaved_changes(self):
        """Check if the form has unsaved changes"""
        current_state = self.get_form_state_string()
        return current_state != self.form_snapshot
    
    def check_unsaved_changes(self, action_name="proceed"):
        """Check for unsaved changes and prompt user. Returns True if OK to proceed."""
        if not self.has_unsaved_changes():
            return True
        
        # Prompt user
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            f"You have unsaved changes.\n\nDo you want to save before you {action_name}?",
            icon='warning'
        )
        
        if result is None:  # Cancel
            return False
        elif result:  # Yes - save first
            self.save_configuration_settings()
            return True
        else:  # No - discard changes
            return True
    
    def on_closing(self):
        """Handle window close event"""
        if self.check_unsaved_changes("exit"):
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
            if not self.check_unsaved_changes("switch tabs"):
                # User cancelled - switch back to Setup tab
                self.notebook.select(self.setup_tab)
                self.previous_tab_index = 0
                return
            
            # CRITICAL: Ensure password is set for networked databases before switching tabs
            # This prevents authentication errors when Session tab tries to connect
            db_type = self.db_type_var.get()
            if db_type in ["postgres", "supabase", "mysql"]:
                # Make sure password is set in database config
                password = self.db_password_var.get().strip()
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
        db_type = self.db_type_var.get()
        
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
        
        # Check required folders (check if variables exist first)
        backup_folder = ""
        trail_maps_folder = ""
        
        if hasattr(self, 'backup_path_var'):
            backup_folder = self.backup_path_var.get().strip()
        
        if hasattr(self, 'folder_path_var'):
            trail_maps_folder = self.folder_path_var.get().strip()
        
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
    
    def run(self):
        """Start the application"""
        self.root.mainloop()
