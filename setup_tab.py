"""
Setup Tab Module for Air-Scenting Logger

This module contains all Setup tab UI and logic, extracted and refactored
from the main ui.py file. All widgets are prefixed with s_ to avoid naming
collisions.

Uses the centralized sv module for StringVars.

Author: Refactored by AI Assistant
Date: 2025-12-31
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import json
import os
from datetime import datetime
from getpass import getuser
from sqlalchemy import text
import sv  # Import centralized StringVars module
from ui_database import DatabaseOperations
from ui_misc_data_ops import MiscDataOperations
import ui_utils


class SetupTab:
    """Manages the Setup tab UI and all related operations"""
    
    def __init__(self, parent_ui):
        """
        Initialize Setup tab manager
        
        Args:
            parent_ui: Reference to main AirScentingUI instance
        """
        self.ui = parent_ui
        
        # Initialize Setup tab widgets (will be created in setup_setup_tab)
        # Note: StringVars are in sv module, not here
        self.s_create_db_btn = None
        self.s_location_listbox = None
        self.s_add_location_btn = None
        self.s_remove_location_btn = None
        self.s_dog_listbox = None
        self.s_add_dog_btn = None
        self.s_remove_dog_btn = None
        self.s_terrain_tree = None
        self.s_add_terrain_btn = None
        self.s_remove_terrain_btn = None
        self.s_move_terrain_up_btn = None
        self.s_move_terrain_down_btn = None
        self.s_distraction_type_tree = None
        self.s_add_distraction_type_btn = None
        self.s_remove_distraction_type_btn = None
        self.s_move_distraction_type_up_btn = None
        self.s_move_distraction_type_down_btn = None
    
    def get_default_distraction_types(self):
        """Get the default distraction type list"""
        return [
            "Critter", "Horse", "Loud noise", "Motorcycle", "Hikers", 
            "Cow", "Vehicle"
        ]


    def setup_setup_tab(self):
        """Setup the Setup tab with all configuration options"""
        # StringVars are in sv module - no need to create them here
        
        # Create scrollable frame
        canvas = tk.Canvas(self.ui.setup_tab)
        scrollbar = ttk.Scrollbar(self.ui.setup_tab, orient="vertical", command=canvas.yview)
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
        
        # REMOVED: sv.db_type = tk.StringVar(value=self.ui.config.get("db_type", "sqlite"))  # StringVar already in sv module
        
        radio_container = tk.Frame(db_type_frame)
        radio_container.pack(pady=5)
        
        tk.Radiobutton(radio_container, text="SQLite", variable=sv.db_type, 
                      value="sqlite", command=self.ui.on_db_type_changed).pack(side="left", padx=20)
        tk.Radiobutton(radio_container, text="PostgreSQL", variable=sv.db_type, 
                      value="postgres", command=self.ui.on_db_type_changed).pack(side="left", padx=20)
        tk.Radiobutton(radio_container, text="Supabase", variable=sv.db_type, 
                      value="supabase", command=self.ui.on_db_type_changed).pack(side="left", padx=20)
        tk.Radiobutton(radio_container, text="MySQL", variable=sv.db_type, 
                      value="mysql", command=self.ui.on_db_type_changed).pack(side="left", padx=20)
        
        # Database Password (for postgres, supabase, mysql)
        self.s_db_password_frame = tk.Frame(db_type_frame)
        self.s_db_password_frame.pack(pady=5)
        
        tk.Label(self.s_db_password_frame, text="Database Password:").pack(side="left", padx=5)
        self.s_db_password_entry = tk.Entry(self.s_db_password_frame, textvariable=sv.db_password, 
                                          width=30, show="*")
        self.s_db_password_entry.pack(side="left", padx=5)
        
        # Add right-click context menu for password entry (Cut/Copy/Paste)
        self.ui.add_entry_context_menu(self.s_db_password_entry)
        
        # Show/Hide password checkbox
        tk.Checkbutton(self.s_db_password_frame, text="Show", variable=sv.show_password,
                      command=self.ui.toggle_password_visibility).pack(side="left", padx=5)
        
        # Remember Password checkbox
        tk.Checkbutton(self.s_db_password_frame, text="Remember", variable=sv.remember_password).pack(side="left", padx=5)
        
        # Forget Password button
        tk.Button(self.s_db_password_frame, text="Forget Saved Password", 
                 command=self.ui.forget_password, width=18).pack(side="left", padx=5)
        
        # Add trace to update Create Database button when database type changes
        sv.db_type.trace_add('write', self.update_create_db_button_state)
        
        # Initialize button state and password field visibility
        self.ui.root.after(100, self.update_create_db_button_state)
        self.ui.root.after(100, self.ui.on_db_type_changed)
        
        # Database folder selection
        db_frame = tk.LabelFrame(frame, text="Database Folder", padx=10, pady=5)
        db_frame.pack(fill="x", pady=5)
        
        tk.Entry(db_frame, textvariable=sv.db_path, width=70).pack(side="left", padx=5)
        tk.Button(db_frame, text="Browse", command=self.ui.file_ops.select_db_folder).pack(side="left", padx=5)
        self.s_create_db_btn = tk.Button(db_frame, text="Create Database", 
                                       command=self.create_database, state="disabled")
        self.s_create_db_btn.pack(side="left", padx=5)
        
        # Add trace to db_path_var to enable/disable Create Database button
        sv.db_path.trace_add('write', self.update_create_db_button_state)
        
        # Trail maps folder
        folder_frame = tk.LabelFrame(frame, text="Trail Maps Storage Folder", padx=10, pady=5)
        folder_frame.pack(fill="x", pady=5)
        
        tk.Entry(folder_frame, textvariable=sv.trail_maps_folder, width=70).pack(side="left", padx=5)
        tk.Button(folder_frame, text="Browse", command=self.ui.file_ops.select_folder).pack(side="left", padx=5)
        
        # Backup folder
        backup_frame = tk.LabelFrame(frame, text="Backup Folder", padx=10, pady=5)
        backup_frame.pack(fill="x", pady=5)
        
        tk.Entry(backup_frame, textvariable=sv.backup_folder, width=70).pack(side="left", padx=5)
        tk.Button(backup_frame, text="Browse", command=self.ui.file_ops.select_backup_folder).pack(side="left", padx=5)
        tk.Button(backup_frame, text="Restore Settings from Backup", 
                 command=self.ui.misc_data_ops.restore_settings_from_json).pack(side="left", padx=5)
        
        # Default values
        defaults_frame = tk.LabelFrame(frame, text="Default Values (Optional)", padx=10, pady=5)
        defaults_frame.pack(fill="x", pady=5)
        
        tk.Label(defaults_frame, text="Handler Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        # REMOVED: sv.default_handler = tk.StringVar(value=self.ui.config.get("handler_name", ""))  # StringVar already in sv module
        tk.Entry(defaults_frame, textvariable=sv.default_handler, width=30).grid(row=0, column=1, padx=5, pady=2)
        
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
        
        self.s_location_listbox = tk.Listbox(loc_list_frame, yscrollcommand=loc_scrollbar.set, height=4)
        self.s_location_listbox.pack(side="left", fill="both", expand=True)
        loc_scrollbar.config(command=self.s_location_listbox.yview)
        
        # Populate listbox with locations from database
        self.load_locations_from_database()
        
        # Buttons for managing locations
        loc_button_frame = tk.Frame(locations_frame)
        loc_button_frame.pack(side="right", padx=(10, 0))
        
        tk.Label(loc_button_frame, text="Location:").pack(anchor="w")
        # REMOVED: sv.new_location = tk.StringVar()  # StringVar already in sv module
        location_entry = tk.Entry(loc_button_frame, textvariable=sv.new_location, width=20)
        location_entry.pack(pady=2)
        location_entry.bind('<Return>', lambda e: self.add_location())
        
        self.s_add_location_btn = tk.Button(loc_button_frame, text="Add Location", 
                                         command=self.add_location, width=15, state="disabled")
        self.s_add_location_btn.pack(pady=2)
        
        self.s_remove_location_btn = tk.Button(loc_button_frame, text="Remove Selected", 
                                            command=self.remove_location, width=15, state="disabled")
        self.s_remove_location_btn.pack(pady=2)
        
        # Add trace and selection binding for locations
        sv.new_location.trace_add('write', self.update_location_button_states)
        self.s_location_listbox.bind('<<ListboxSelect>>', self.on_location_select)
        
        # Dog Names Management
        dogs_frame = tk.LabelFrame(column0_container, text="Dog Names", padx=10, pady=5)
        dogs_frame.pack(fill="x")
        
        # Listbox with scrollbar
        list_frame = tk.Frame(dogs_frame)
        list_frame.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.s_dog_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=3)
        self.s_dog_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.s_dog_listbox.yview)
        
        # Populate listbox with dogs from database
        self.load_dogs_from_database()
        
        # Buttons for managing dogs
        button_frame = tk.Frame(dogs_frame)
        button_frame.pack(side="right", padx=(10, 0))
        
        tk.Label(button_frame, text="Dog Name:").pack(anchor="w")
        # REMOVED: sv.new_dog = tk.StringVar()  # StringVar already in sv module
        dog_entry = tk.Entry(button_frame, textvariable=sv.new_dog, width=20)
        dog_entry.pack(pady=2)
        dog_entry.bind('<Return>', lambda e: self.add_dog())
        
        self.s_add_dog_btn = tk.Button(button_frame, text="Add Dog", 
                                     command=self.add_dog, width=15, state="disabled")
        self.s_add_dog_btn.pack(pady=2)
        
        self.s_remove_dog_btn = tk.Button(button_frame, text="Remove Selected", 
                                       command=self.remove_dog, width=15, state="disabled")
        self.s_remove_dog_btn.pack(pady=2)
        
        # Add trace to entry field and bind listbox selection
        sv.new_dog.trace_add('write', self.update_dog_button_states)
        self.s_dog_listbox.bind('<<ListboxSelect>>', self.on_dog_select)
        
        # Terrain Types Management
        terrain_frame = tk.LabelFrame(management_container, text="Terrain Types", padx=10, pady=5)
        terrain_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Treeview with scrollbar
        tree_frame = tk.Frame(terrain_frame)
        tree_frame.pack(side="left", fill="both", expand=True)
        
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")
        
        self.s_terrain_tree = ttk.Treeview(tree_frame, columns=('Terrain',), show='tree headings', 
                                        yscrollcommand=tree_scrollbar.set, height=8, selectmode='browse')
        self.s_terrain_tree.heading('#0', text='#')
        self.s_terrain_tree.heading('Terrain', text='Terrain Type')
        self.s_terrain_tree.column('#0', width=40)
        self.s_terrain_tree.column('Terrain', width=150)
        self.s_terrain_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.config(command=self.s_terrain_tree.yview)
        
        # Populate treeview with terrain types from database
        self.load_terrain_from_database()
        
        # Buttons for managing terrain types
        terrain_button_frame = tk.Frame(terrain_frame)
        terrain_button_frame.pack(side="right", padx=(10, 0))
        
        tk.Label(terrain_button_frame, text="Terrain Type:").pack(anchor="w")
        # REMOVED: sv.new_terrain = tk.StringVar()  # StringVar already in sv module
        terrain_entry = tk.Entry(terrain_button_frame, textvariable=sv.new_terrain, width=20)
        terrain_entry.pack(pady=2)
        terrain_entry.bind('<Return>', lambda e: self.add_terrain_type())
        
        self.s_add_terrain_btn = tk.Button(terrain_button_frame, text="Add Terrain Type", 
                                        command=self.add_terrain_type, width=15, state="disabled")
        self.s_add_terrain_btn.pack(pady=2)
        
        self.s_remove_terrain_btn = tk.Button(terrain_button_frame, text="Remove Selected", 
                                           command=self.remove_terrain_type, width=15, state="disabled")
        self.s_remove_terrain_btn.pack(pady=2)
        
        self.s_move_terrain_up_btn = tk.Button(terrain_button_frame, text="Move Up", 
                                            command=self.move_terrain_up, width=15, state="disabled")
        self.s_move_terrain_up_btn.pack(pady=2)
        
        self.s_move_terrain_down_btn = tk.Button(terrain_button_frame, text="Move Down", 
                                              command=self.move_terrain_down, width=15, state="disabled")
        self.s_move_terrain_down_btn.pack(pady=2)
        
        tk.Button(terrain_button_frame, text="Restore Defaults", 
                 command=self.restore_default_terrain_types, width=15).pack(pady=2)
        
        # Add trace and selection binding
        sv.new_terrain.trace_add('write', self.update_terrain_button_states)
        self.s_terrain_tree.bind('<<TreeviewSelect>>', self.on_terrain_select)
        
        # Distraction Types Management
        distraction_frame = tk.LabelFrame(management_container, text="Distraction Types", padx=10, pady=5)
        distraction_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        # Treeview with scrollbar
        dist_tree_frame = tk.Frame(distraction_frame)
        dist_tree_frame.pack(side="left", fill="both", expand=True)
        
        dist_tree_scrollbar = ttk.Scrollbar(dist_tree_frame, orient="vertical")
        dist_tree_scrollbar.pack(side="right", fill="y")
        
        self.s_distraction_type_tree = ttk.Treeview(dist_tree_frame, columns=('Distraction',), show='tree headings', 
                                                 yscrollcommand=dist_tree_scrollbar.set, height=8, selectmode='browse')
        self.s_distraction_type_tree.heading('#0', text='#')
        self.s_distraction_type_tree.heading('Distraction', text='Distraction Type')
        self.s_distraction_type_tree.column('#0', width=40)
        self.s_distraction_type_tree.column('Distraction', width=150)
        self.s_distraction_type_tree.pack(side="left", fill="both", expand=True)
        dist_tree_scrollbar.config(command=self.s_distraction_type_tree.yview)
        
        # Populate treeview with distraction types from database
        self.load_distraction_from_database()
        
        # Buttons for managing distraction types
        distraction_button_frame = tk.Frame(distraction_frame)
        distraction_button_frame.pack(side="right", padx=(10, 0))
        
        tk.Label(distraction_button_frame, text="Distraction Type:").pack(anchor="w")
        # REMOVED: sv.new_distraction = tk.StringVar()  # StringVar already in sv module
        distraction_entry = tk.Entry(distraction_button_frame, textvariable=sv.new_distraction, width=20)
        distraction_entry.pack(pady=2)
        distraction_entry.bind('<Return>', lambda e: self.add_distraction_type())
        
        self.s_add_distraction_type_btn = tk.Button(distraction_button_frame, text="Add Distraction Type", 
                                                 command=self.add_distraction_type, width=17, state="disabled")
        self.s_add_distraction_type_btn.pack(pady=2)
        
        self.s_remove_distraction_type_btn = tk.Button(distraction_button_frame, text="Remove Selected", 
                                                    command=self.remove_distraction_type, width=17, state="disabled")
        self.s_remove_distraction_type_btn.pack(pady=2)
        
        self.s_move_distraction_type_up_btn = tk.Button(distraction_button_frame, text="Move Up", 
                                                     command=self.move_distraction_up, width=17, state="disabled")
        self.s_move_distraction_type_up_btn.pack(pady=2)
        
        self.s_move_distraction_type_down_btn = tk.Button(distraction_button_frame, text="Move Down", 
                                                       command=self.move_distraction_down, width=17, state="disabled")
        self.s_move_distraction_type_down_btn.pack(pady=2)
        
        tk.Button(distraction_button_frame, text="Restore Defaults", 
                 command=self.restore_default_distraction_types, width=17).pack(pady=2)
        
        # Add trace and selection binding
        sv.new_distraction.trace_add('write', self.update_distraction_type_button_states)
        self.s_distraction_type_tree.bind('<<TreeviewSelect>>', self.on_distraction_type_select)
        
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




    def select_db_folder(self):
        """Select database folder"""
        folder = filedialog.askdirectory(title="Select Database Folder")
        if folder:
            sv.db_path.set(folder)
            self.ui.machine_db_path = folder

    
    def select_folder(self):
        """Select trail maps folder"""
        folder = filedialog.askdirectory(title="Select Trail Maps Storage Folder")
        if folder:
            sv.trail_maps_folder.set(folder)

    def select_backup_folder(self):
        """Select backup folder"""
        folder = filedialog.askdirectory(title="Select Backup Folder")
        if folder:
            sv.backup_folder.set(folder)
            self.ui.machine_backup_folder = folder

    def update_create_db_button_state(self, *args):
        """Enable/disable Create Database button based on folder selection and database type"""
        db_type = sv.db_type.get()
        has_folder = bool(sv.db_path.get().strip())
        
        # For SQLite, require folder. For postgres/supabase, always enable
        if db_type == "sqlite":
            self.s_create_db_btn.config(state="normal" if has_folder else "disabled")
        else:  # postgres or supabase
            self.s_create_db_btn.config(state="normal")

    def create_database(self):
        """Create or rebuild database schema"""
        from pathlib import Path
        
        # Get selected database type
        db_type = sv.db_type.get()
        
        if db_type == "sqlite":
            # SQLite requires a folder
            folder = sv.db_path.get().strip()
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
                    
                    # Force garbage collection to release connections
                    import gc
                    gc.collect()
                    
                    # Wait for OS to release file locks
                    import time
                    time.sleep(1.0)
                    
                    sv.status.set("Closed database connections...")
                    
                    # Give OS time to release file locks (especially on Windows)
                    import time
                    time.sleep(0.5)
                except Exception as e:
                    print(f"Note: Could not dispose engine: {e}")
                
                # Delete existing database AND WAL files
                try:
                    # Delete main database file
                    if db_path.exists():
                        db_path.unlink()
                    
                    # Delete WAL files if they exist
                    wal_file = Path(str(db_path) + "-wal")
                    shm_file = Path(str(db_path) + "-shm")
                    if wal_file.exists():
                        wal_file.unlink()
                    if shm_file.exists():
                        shm_file.unlink()
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
                
                sv.status.set(f"Database created: {db_path}")
                messagebox.showinfo(
                    "Success", 
                    f"SQLite database created successfully!\n\n{db_path}\n\n"
                    f"Schema initialized with training_sessions table."
                )
                
                # Offer to restore from JSON backups
                self.ui.misc_data_ops.restore_from_json_backups("sqlite")
                
                # Offer to load default terrain and distraction types
                self.ui.misc_data_ops.offer_load_default_types("sqlite")
                
                # Update session number and UI after database recreation
                sv.session_number.set(str(DatabaseOperations(self.ui).get_next_session_number()))
                self.ui.selected_sessions = []
                self.ui.selected_sessions_index = -1
                self.ui.navigation.update_navigation_buttons()
                # Clear form to new entry state
                self.ui.set_date(datetime.now().strftime("%Y-%m-%d"))
                sv.session_purpose.set("")
                sv.field_support.set("")
                sv.dog.set("")
                sv.search_area_size.set("")
                sv.num_subjects.set("")
                sv.handler_knowledge.set("")
                sv.weather.set("")
                sv.temperature.set("")
                sv.wind_direction.set("")
                sv.wind_speed.set("")
                sv.search_type.set("")
                sv.drive_level.set("")
                sv.subjects_found.set("")
                # Update subjects_found combo state (will disable since num_subjects is blank)
                self.ui.form_mgmt.update_subjects_found()
                
                # Refresh dog list on Setup tab (new database has no dogs)
                self.refresh_dog_list()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create database:\n{e}\n\n{type(e).__name__}")
                import traceback
                traceback.print_exc()
        
        else:  # postgres or supabase
            # For Supabase, check if password has been configured
            if db_type == "supabase":
                import config
                supabase_url = config.DB_CONFIG["supabase"]["url"]
                if "[YOUR-PASSWORD]" in supabase_url:
                    messagebox.showerror(
                        "Password Not Configured",
                        "Supabase password has not been set!\n\n"
                        "Please edit config.py line 24 and replace:\n"
                        "[YOUR-PASSWORD]\n\n"
                        "with your actual Supabase database password."
                    )
                    return
            
            # For PostgreSQL/Supabase, check if tables exist and offer to rebuild
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
                
                # Check if training_sessions table exists
                with database.get_connection() as conn:
                    check_query = text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'training_sessions'
                        )
                    """)
                    
                    result = conn.execute(check_query)
                    table_exists = result.scalar()
                
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
                    drop_tables()
                    sv.status.set("Dropped existing tables...")
                
                # Create tables
                create_tables()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                sv.status.set(f"{db_type.title()} schema created successfully")
                messagebox.showinfo(
                    "Success",
                    f"{db_type.title()} database schema created successfully!\n\n"
                    f"Tables initialized:\n"
                    f"  - training_sessions"
                )
                
                # Offer to restore from JSON backups
                self.ui.misc_data_ops.restore_from_json_backups(db_type)
                
                # Offer to load default terrain and distraction types
                self.ui.misc_data_ops.offer_load_default_types(db_type)
                
                # Update session number and UI after database recreation
                sv.session_number.set(str(DatabaseOperations(self.ui).get_next_session_number()))
                self.ui.selected_sessions = []
                self.ui.selected_sessions_index = -1
                self.ui.navigation.update_navigation_buttons()
                # Clear form to new entry state
                self.ui.set_date(datetime.now().strftime("%Y-%m-%d"))
                sv.session_purpose.set("")
                sv.field_support.set("")
                sv.dog.set("")
                sv.search_area_size.set("")
                sv.num_subjects.set("")
                sv.handler_knowledge.set("")
                sv.weather.set("")
                sv.temperature.set("")
                sv.wind_direction.set("")
                sv.wind_speed.set("")
                sv.search_type.set("")
                sv.drive_level.set("")
                sv.subjects_found.set("")
                # Update subjects_found combo state (will disable since num_subjects is blank)
                self.ui.form_mgmt.update_subjects_found()
                
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
                    f"1. Database connection is configured in config.py\n"
                    f"2. Password is set correctly (replace [YOUR-PASSWORD])\n"
                    f"3. You have network access to Supabase\n"
                    f"4. Credentials are correct"
                )
                import traceback
                traceback.print_exc()
    

    def load_locations_from_database(self):
        """Load training locations from database into Setup tab listbox"""
        db_type = sv.db_type.get()
        
        # For SQLite, check if database file exists before trying to connect
        if db_type == "sqlite":
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            if not os.path.exists(db_path):
                # Database doesn't exist - clear listbox and return
                if hasattr(self, 's_location_listbox'):
                    self.s_location_listbox.delete(0, tk.END)
                return
        
        try:
            # Temporarily switch to selected database type
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            # Reload database module
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            from sqlalchemy import text
            
            # Query training_locations table
            with database.get_connection() as conn:
                result = conn.execute(text("SELECT name FROM training_locations ORDER BY name"))
                locations = [row[0] for row in result]
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Clear and populate listbox
            self.s_location_listbox.delete(0, tk.END)
            for location in locations:
                self.s_location_listbox.insert(tk.END, location)
                
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
            
            # If table doesn't exist yet, silently skip (database will be created later)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                # Clear the listbox
                if hasattr(self, 's_location_listbox'):
                    self.s_location_listbox.delete(0, tk.END)
                # Don't print - this is expected before database is created
            else:
                print(f"Error loading locations: {e}")

    def refresh_location_list(self):
        """Refresh the location combobox in Entry tab"""
        db_type = sv.db_type.get()
        
        # For SQLite, check if database file exists before trying to connect
        if db_type == "sqlite":
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            if not os.path.exists(db_path):
                # Database doesn't exist - clear combobox and return
                if hasattr(self.ui, 'a_location_combo'):
                    self.ui.a_location_combo['values'] = []
                return
        
        try:
            # Temporarily switch to selected database type
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            # Reload database module
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            from sqlalchemy import text
            
            # Query training_locations table
            with database.get_connection() as conn:
                result = conn.execute(text("SELECT name FROM training_locations ORDER BY name"))
                locations = [row[0] for row in result]
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Update combobox
            if hasattr(self.ui, 'a_location_combo'):
                self.ui.a_location_combo['values'] = locations
                
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
            
            # If table doesn't exist yet, silently skip
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                # Clear the combobox
                #if hasattr(self.ui, 'a_location_combo'):   ahg
                if hasattr(self.ui, 'a_location_combo'):
                    #self.ui.a_location_combo['values'] = []   ahg
                    self.ui.a_location_combo['values'] = []
            else:
                print(f"Error refreshing location list: {e}")

    def load_terrain_from_database(self):
        """Load terrain types from database into Setup tab treeview"""
        db_type = sv.db_type.get()
        
        # For SQLite, check if database file exists before trying to connect
        if db_type == "sqlite":
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            if not os.path.exists(db_path):
                # Database doesn't exist - clear treeview and return
                if hasattr(self, 'terrain_tree'):
                    self.s_terrain_tree.delete(*self.s_terrain_tree.get_children())
                return
        
        try:
            # Temporarily switch to selected database type
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            # Reload database module
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            from sqlalchemy import text
            
            # Query terrain_types table
            with database.get_connection() as conn:
                result = conn.execute(text("SELECT name FROM terrain_types ORDER BY name"))
                terrain_types = [row[0] for row in result]
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Clear and populate treeview
            self.s_terrain_tree.delete(*self.s_terrain_tree.get_children())
            for idx, terrain in enumerate(terrain_types, 1):
                self.s_terrain_tree.insert('', tk.END, text=str(idx), values=(terrain,))
            
            # Also update Entry tab terrain combo box
            if hasattr(self.ui, 'a_terrain_combo'):
                self.ui.a_terrain_combo['values'] = terrain_types
                
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
            
            # If table doesn't exist yet, silently skip
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                # Clear the treeview
                if hasattr(self, 'terrain_tree'):
                    self.s_terrain_tree.delete(*self.s_terrain_tree.get_children())
            else:
                print(f"Error loading terrain types: {e}")

    def load_distraction_from_database(self):
        """Load distraction types from database into Setup tab treeview"""
        db_type = sv.db_type.get()
        
        # For SQLite, check if database file exists before trying to connect
        if db_type == "sqlite":
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            if not os.path.exists(db_path):
                # Database doesn't exist - clear treeview and return
                if hasattr(self, 'distraction_type_tree'):
                    self.s_distraction_type_tree.delete(*self.s_distraction_type_tree.get_children())
                return
        
        try:
            # Temporarily switch to selected database type
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            # Reload database module
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            from sqlalchemy import text
            
            # Query distraction_types table
            with database.get_connection() as conn:
                result = conn.execute(text("SELECT name FROM distraction_types ORDER BY name"))
                distraction_types = [row[0] for row in result]
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Clear and populate treeview
            self.s_distraction_type_tree.delete(*self.s_distraction_type_tree.get_children())
            for idx, distraction in enumerate(distraction_types, 1):
                self.s_distraction_type_tree.insert('', tk.END, text=str(idx), values=(distraction,))
                
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
            
            # If table doesn't exist yet, silently skip
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                # Clear the treeview
                if hasattr(self, 'distraction_type_tree'):
                    self.s_distraction_type_tree.delete(*self.s_distraction_type_tree.get_children())
            else:
                print(f"Error loading distraction types: {e}")

    def update_location_button_states(self, *args):
        """Enable/disable location buttons based on entry content"""
        has_text = bool(sv.new_location.get().strip())
        self.s_add_location_btn.config(state="normal" if has_text else "disabled")

    def on_location_select(self, event):
        """Handle location selection in listbox"""
        selection = self.s_location_listbox.curselection()
        self.s_remove_location_btn.config(state="normal" if selection else "disabled")

    def add_location(self):
        """Add a new training location to database"""
        location = sv.new_location.get().strip()
        if location:
            db_type = sv.db_type.get()
            
            try:
                # Temporarily switch to selected database type
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                # Reload database module
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Insert into training_locations table
                with database.get_connection() as conn:
                    conn.execute(
                        text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                        {"name": location, "user_name": ui_utils.get_username()}
                    )
                    conn.commit()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                # Refresh UI
                self.load_locations_from_database()
                self.refresh_location_list()
                
                sv.new_location.set("")
                sv.status.set(f"Added location: {location}")
                
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
                
                if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                    messagebox.showinfo("Duplicate", f"Location '{location}' already exists")
                else:
                    messagebox.showerror("Database Error", f"Failed to add location:\n{e}")
                    print(f"Error adding location: {e}")

    def remove_location(self):
        """Remove selected training location from database"""
        selection = self.s_location_listbox.curselection()
        if selection:
            location = self.s_location_listbox.get(selection[0])
            
            result = messagebox.askyesno("Confirm Delete", 
                                        f"Delete location '{location}'?")
            if not result:
                return
            
            db_type = sv.db_type.get()
            
            try:
                # Temporarily switch to selected database type
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                # Reload database module
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Delete from training_locations table
                with database.get_connection() as conn:
                    conn.execute(
                        text("DELETE FROM training_locations WHERE name = :name"),
                        {"name": location}
                    )
                    conn.commit()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                # Refresh UI
                self.load_locations_from_database()
                self.refresh_location_list()
                
                sv.status.set(f"Removed location: {location}")
                self.s_remove_location_btn.config(state="disabled")
                
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
                
                messagebox.showerror("Database Error", f"Failed to remove location:\n{e}")
                print(f"Error removing location: {e}")
    

    def load_dogs_from_database(self):
        """Load dog names from database into listbox"""
        db_type = sv.db_type.get()
        
        # print(f"DEBUG load_dogs_from_database: db_type={db_type}")  # DEBUG
        
        # For SQLite, check if database file exists before trying to connect
        if db_type == "sqlite":
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            # print(f"DEBUG load_dogs_from_database: db_path={db_path}, exists={os.path.exists(db_path)}")  # DEBUG
            if not os.path.exists(db_path):
                # Database doesn't exist - clear listbox and return
                if hasattr(self, 's_dog_listbox'):
                    self.s_dog_listbox.delete(0, tk.END)
                # print(f"DEBUG load_dogs_from_database: Database doesn't exist, returning")  # DEBUG
                return
        
        try:
            # Temporarily switch to selected database type
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            # Reload database module
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            from sqlalchemy import text
            
            # Query dogs table
            with database.get_connection() as conn:
                result = conn.execute(text("SELECT name FROM dogs ORDER BY name"))
                dogs = [row[0] for row in result]
            
            # print(f"DEBUG load_dogs_from_database: Found {len(dogs)} dogs: {dogs}")  # DEBUG
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Clear and populate listbox
            self.s_dog_listbox.delete(0, tk.END)
            for dog in dogs:
                self.s_dog_listbox.insert(tk.END, dog)
            
            # print(f"DEBUG load_dogs_from_database: Populated listbox with {len(dogs)} dogs")  # DEBUG
                
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
            
            # If table doesn't exist yet, silently skip (database will be created later)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                # Clear the listbox
                if hasattr(self, 's_dog_listbox'):
                    self.s_dog_listbox.delete(0, tk.END)
                # Don't print - this is expected before database is created
            else:
                print(f"Error loading dogs: {e}")

    def refresh_dog_list(self):
        """Refresh the dog combobox in Entry tab"""
        db_type = sv.db_type.get()
        
        # print(f"DEBUG refresh_dog_list: db_type={db_type}")  # DEBUG
        
        # For SQLite, check if database file exists before trying to connect
        if db_type == "sqlite":
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            # print(f"DEBUG refresh_dog_list: db_path={db_path}, exists={os.path.exists(db_path)}")  # DEBUG
            if not os.path.exists(db_path):
                # Database doesn't exist - clear combobox/listbox and return
                if hasattr(self.ui, 'a_dog_combo'):
                    self.ui.a_dog_combo['values'] = []
                if hasattr(self, 's_dog_listbox'):
                    self.s_dog_listbox.delete(0, tk.END)
                # print(f"DEBUG refresh_dog_list: Database doesn't exist, returning")  # DEBUG
                return
        
        try:
            # Temporarily switch to selected database type
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            # Reload database module
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            from sqlalchemy import text
            
            # Query dogs table
            with database.get_connection() as conn:
                result = conn.execute(text("SELECT name FROM dogs ORDER BY name"))
                dogs = [row[0] for row in result]
            
            # print(f"DEBUG refresh_dog_list: Found {len(dogs)} dogs: {dogs}")  # DEBUG
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Update combobox
            if hasattr(self.ui, 'a_dog_combo'):
                self.ui.a_dog_combo['values'] = dogs
                # print(f"DEBUG refresh_dog_list: Updated dog_combo with {len(dogs)} dogs")  # DEBUG
            
            # Also update Setup tab listbox
            self.s_dog_listbox.delete(0, tk.END)
            for dog in dogs:
                self.s_dog_listbox.insert(tk.END, dog)
            
            # print(f"DEBUG refresh_dog_list: Updated dog_listbox with {len(dogs)} dogs")  # DEBUG
                
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
            
            # If database/tables don't exist yet, silently skip (they'll be created later)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                # Clear the combobox and listbox
                if hasattr(self.ui, 'a_dog_combo'):
                    self.ui.a_dog_combo['values'] = []
                if hasattr(self, 's_dog_listbox'):
                    self.s_dog_listbox.delete(0, tk.END)
                # Don't print error - this is expected before database is created
            else:
                # Unexpected error - print it
                print(f"Error refreshing dog list: {e}")

    def update_dog_button_states(self, *args):
        """Enable/disable dog buttons based on entry content"""
        has_text = bool(sv.new_dog.get().strip())
        self.s_add_dog_btn.config(state="normal" if has_text else "disabled")

    def on_dog_select(self, event):
        """Handle dog selection in listbox"""
        selection = self.s_dog_listbox.curselection()
        self.s_remove_dog_btn.config(state="normal" if selection else "disabled")

    def add_dog(self):
        """Add a new dog name"""
        dog_name = sv.new_dog.get().strip()
        if dog_name:
            # Check database type and selected type
            db_type = sv.db_type.get()
            
            try:
                # Temporarily switch to selected database type
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                # Reload database module
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Insert into dogs table with user_name
                with database.get_connection() as conn:
                    conn.execute(
                        text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                        {"name": dog_name, "user_name": ui_utils.get_username()}
                    )
                    conn.commit()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                # Update listbox
                self.s_dog_listbox.insert(tk.END, dog_name)
                
                # Update dog combobox in Entry tab if it exists
                if hasattr(self.ui, 'a_dog_combo'):
                    self.refresh_dog_list()
                
                sv.new_dog.set("")
                sv.status.set(f"Added dog: {dog_name}")
                
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
                
                if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                    messagebox.showinfo("Duplicate", f"Dog '{dog_name}' already exists")
                else:
                    messagebox.showerror("Database Error", f"Failed to add dog:\n{e}")
                    print(f"Error adding dog: {e}")

    def remove_dog(self):
        """Remove selected dog name"""
        selection = self.s_dog_listbox.curselection()
        if selection:
            dog_name = self.s_dog_listbox.get(selection[0])
            
            # Confirm deletion
            result = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete dog '{dog_name}'?\n\n"
                "This will not delete training sessions for this dog."
            )
            if not result:
                return
            
            db_type = sv.db_type.get()
            
            try:
                # Temporarily switch to selected database type
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                # Reload database module
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Delete from dogs table
                with database.get_connection() as conn:
                    conn.execute(
                        text("DELETE FROM dogs WHERE name = :name"),
                        {"name": dog_name}
                    )
                    conn.commit()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                # Update listbox
                self.s_dog_listbox.delete(selection[0])
                
                # Update dog combobox in Entry tab if it exists
                if hasattr(self.ui, 'a_dog_combo'):
                    self.refresh_dog_list()
                
                sv.status.set(f"Removed dog: {dog_name}")
                self.s_remove_dog_btn.config(state="disabled")
                
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
                
                messagebox.showerror("Database Error", f"Failed to remove dog:\n{e}")
                print(f"Error removing dog: {e}")
    

    def update_terrain_button_states(self, *args):
        """Enable/disable terrain buttons based on entry content and selection"""
        has_text = bool(sv.new_terrain.get().strip())
        self.s_add_terrain_btn.config(state="normal" if has_text else "disabled")

    def on_terrain_select(self, event):
        """Handle terrain type selection"""
        selection = self.s_terrain_tree.selection()
        has_selection = bool(selection)
        self.s_remove_terrain_btn.config(state="normal" if has_selection else "disabled")
        self.s_move_terrain_up_btn.config(state="normal" if has_selection else "disabled")
        self.s_move_terrain_down_btn.config(state="normal" if has_selection else "disabled")

    def add_terrain_type(self):
        """Add a new terrain type to database"""
        terrain = sv.new_terrain.get().strip()
        if terrain:
            db_type = sv.db_type.get()
            
            try:
                # Temporarily switch to selected database type
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                # Reload database module
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Insert into terrain_types table
                with database.get_connection() as conn:
                    conn.execute(
                        text("INSERT INTO terrain_types (name, user_name) VALUES (:name, :user_name)"),
                        {"name": terrain, "user_name": ui_utils.get_username()}
                    )
                    conn.commit()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                # Refresh UI
                self.load_terrain_from_database()
                
                sv.new_terrain.set("")
                sv.status.set(f"Added terrain type: {terrain}")
                
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
                
                if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                    messagebox.showinfo("Duplicate", f"Terrain type '{terrain}' already exists")
                else:
                    messagebox.showerror("Database Error", f"Failed to add terrain type:\n{e}")
                    print(f"Error adding terrain type: {e}")

    def remove_terrain_type(self):
        """Remove selected terrain type from database"""
        selection = self.s_terrain_tree.selection()
        if selection:
            item = selection[0]
            values = self.s_terrain_tree.item(item, 'values')
            terrain = values[0]
            
            result = messagebox.askyesno("Confirm Delete", 
                                        f"Delete terrain type '{terrain}'?")
            if not result:
                return
            
            db_type = sv.db_type.get()
            
            try:
                # Temporarily switch to selected database type
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                # Reload database module
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Delete from terrain_types table
                with database.get_connection() as conn:
                    conn.execute(
                        text("DELETE FROM terrain_types WHERE name = :name"),
                        {"name": terrain}
                    )
                    conn.commit()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                # Refresh UI
                self.load_terrain_from_database()
                
                sv.status.set(f"Removed terrain type: {terrain}")
                
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
                
                messagebox.showerror("Database Error", f"Failed to remove terrain type:\n{e}")
                print(f"Error removing terrain type: {e}")

    def move_terrain_up(self):
        """Move selected terrain type up"""
        selection = self.s_terrain_tree.selection()
        if selection:
            item = selection[0]
            values = self.s_terrain_tree.item(item, 'values')
            terrain = values[0]
            
            existing = self.ui.config.get("terrain_types", [])
            idx = existing.index(terrain)
            if idx > 0:
                # Swap with previous
                existing[idx], existing[idx-1] = existing[idx-1], existing[idx]
                self.ui.config["terrain_types"] = existing
                
                # Rebuild treeview
                self.s_terrain_tree.delete(*self.s_terrain_tree.get_children())
                for i, t in enumerate(existing, 1):
                    new_item = self.s_terrain_tree.insert('', tk.END, text=str(i), values=(t,))
                    if t == terrain:
                        self.s_terrain_tree.selection_set(new_item)
                        self.s_terrain_tree.see(new_item)

    def move_terrain_down(self):
        """Move selected terrain type down"""
        selection = self.s_terrain_tree.selection()
        if selection:
            item = selection[0]
            values = self.s_terrain_tree.item(item, 'values')
            terrain = values[0]
            
            existing = self.ui.config.get("terrain_types", [])
            idx = existing.index(terrain)
            if idx < len(existing) - 1:
                # Swap with next
                existing[idx], existing[idx+1] = existing[idx+1], existing[idx]
                self.ui.config["terrain_types"] = existing
                
                # Rebuild treeview
                self.s_terrain_tree.delete(*self.s_terrain_tree.get_children())
                for i, t in enumerate(existing, 1):
                    new_item = self.s_terrain_tree.insert('', tk.END, text=str(i), values=(t,))
                    if t == terrain:
                        self.s_terrain_tree.selection_set(new_item)
                        self.s_terrain_tree.see(new_item)

    def restore_default_terrain_types(self):
        """Restore default terrain types"""
        result = messagebox.askyesno(
            "Restore Defaults",
            "This will replace your terrain types with the default list. Continue?"
        )
        if result:
            self.ui.config["terrain_types"] = ui_utils.get_default_terrain_types()
            
            # Rebuild treeview
            self.s_terrain_tree.delete(*self.s_terrain_tree.get_children())
            for idx, terrain in enumerate(self.ui.config["terrain_types"], 1):
                self.s_terrain_tree.insert('', tk.END, text=str(idx), values=(terrain,))
            
            sv.status.set("Restored default terrain types")
    

    def update_distraction_type_button_states(self, *args):
        """Enable/disable distraction type buttons"""
        has_text = bool(sv.new_distraction.get().strip())
        self.s_add_distraction_type_btn.config(state="normal" if has_text else "disabled")

    def on_distraction_type_select(self, event):
        """Handle distraction type selection"""
        selection = self.s_distraction_type_tree.selection()
        has_selection = bool(selection)
        self.s_remove_distraction_type_btn.config(state="normal" if has_selection else "disabled")
        self.s_move_distraction_type_up_btn.config(state="normal" if has_selection else "disabled")
        self.s_move_distraction_type_down_btn.config(state="normal" if has_selection else "disabled")

    def add_distraction_type(self):
        """Add a new distraction type to database"""
        distraction = sv.new_distraction.get().strip()
        if distraction:
            db_type = sv.db_type.get()
            
            try:
                # Temporarily switch to selected database type
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                # Reload database module
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Insert into distraction_types table
                with database.get_connection() as conn:
                    conn.execute(
                        text("INSERT INTO distraction_types (name, user_name) VALUES (:name, :user_name)"),
                        {"name": distraction, "user_name": ui_utils.get_username()}
                    )
                    conn.commit()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                # Refresh UI
                self.load_distraction_from_database()
                
                sv.new_distraction.set("")
                sv.status.set(f"Added distraction type: {distraction}")
                
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
                
                if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                    messagebox.showinfo("Duplicate", f"Distraction type '{distraction}' already exists")
                else:
                    messagebox.showerror("Database Error", f"Failed to add distraction type:\n{e}")
                    print(f"Error adding distraction type: {e}")
    
                
                sv.new_distraction.set("")
                sv.status.set(f"Added distraction type: {distraction}")

    def remove_distraction_type(self):
        """Remove selected distraction type from database"""
        selection = self.s_distraction_type_tree.selection()
        if selection:
            item = selection[0]
            values = self.s_distraction_type_tree.item(item, 'values')
            distraction = values[0]
            
            result = messagebox.askyesno("Confirm Delete", 
                                        f"Delete distraction type '{distraction}'?")
            if not result:
                return
            
            db_type = sv.db_type.get()
            
            try:
                # Temporarily switch to selected database type
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                # Reload database module
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                from sqlalchemy import text
                
                # Delete from distraction_types table
                with database.get_connection() as conn:
                    conn.execute(
                        text("DELETE FROM distraction_types WHERE name = :name"),
                        {"name": distraction}
                    )
                    conn.commit()
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
                # Refresh UI
                self.load_distraction_from_database()
                
                sv.status.set(f"Removed distraction type: {distraction}")
                
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
                
                messagebox.showerror("Database Error", f"Failed to remove distraction type:\n{e}")
                print(f"Error removing distraction type: {e}")

    def move_distraction_up(self):
        """Move selected distraction type up"""
        selection = self.s_distraction_type_tree.selection()
        if selection:
            item = selection[0]
            values = self.s_distraction_type_tree.item(item, 'values')
            distraction = values[0]
            
            existing = self.ui.config.get("distraction_types", [])
            idx = existing.index(distraction)
            if idx > 0:
                # Swap with previous
                existing[idx], existing[idx-1] = existing[idx-1], existing[idx]
                self.ui.config["distraction_types"] = existing
                
                # Rebuild treeview
                self.s_distraction_type_tree.delete(*self.s_distraction_type_tree.get_children())
                for i, d in enumerate(existing, 1):
                    new_item = self.s_distraction_type_tree.insert('', tk.END, text=str(i), values=(d,))
                    if d == distraction:
                        self.s_distraction_type_tree.selection_set(new_item)
                        self.s_distraction_type_tree.see(new_item)

    def move_distraction_down(self):
        """Move selected distraction type down"""
        selection = self.s_distraction_type_tree.selection()
        if selection:
            item = selection[0]
            values = self.s_distraction_type_tree.item(item, 'values')
            distraction = values[0]
            
            existing = self.ui.config.get("distraction_types", [])
            idx = existing.index(distraction)
            if idx < len(existing) - 1:
                # Swap with next
                existing[idx], existing[idx+1] = existing[idx+1], existing[idx]
                self.ui.config["distraction_types"] = existing
                
                # Rebuild treeview
                self.s_distraction_type_tree.delete(*self.s_distraction_type_tree.get_children())
                for i, d in enumerate(existing, 1):
                    new_item = self.s_distraction_type_tree.insert('', tk.END, text=str(i), values=(d,))
                    if d == distraction:
                        self.s_distraction_type_tree.selection_set(new_item)
                        self.s_distraction_type_tree.see(new_item)

    def restore_default_distraction_types(self):
        """Restore default distraction types"""
        result = messagebox.askyesno(
            "Restore Defaults",
            "This will replace your distraction types with the default list. Continue?"
        )
        if result:
            self.ui.config["distraction_types"] = ui_utils.get_default_distraction_types()
            
            # Rebuild treeview
            self.s_distraction_type_tree.delete(*self.s_distraction_type_tree.get_children())
            for idx, distraction in enumerate(self.ui.config["distraction_types"], 1):
                self.s_distraction_type_tree.insert('', tk.END, text=str(idx), values=(distraction,))
            
            sv.status.set("Restored default distraction types")
    

    def save_configuration_settings(self):
        """Save all configuration settings"""
        # Check for text in entry fields that hasn't been added
        unadded_items = []
        if sv.new_location.get().strip():
            unadded_items.append(f"Location: '{sv.new_location.get().strip()}'")
        if sv.new_dog.get().strip():
            unadded_items.append(f"Dog: '{sv.new_dog.get().strip()}'")
        if sv.new_terrain.get().strip():
            unadded_items.append(f"Terrain: '{sv.new_terrain.get().strip()}'")
        if sv.new_distraction.get().strip():
            unadded_items.append(f"Distraction: '{sv.new_distraction.get().strip()}'")
        
        if unadded_items:
            message = "You have typed text that hasn't been added:\n\n" + "\n".join(unadded_items)
            message += "\n\nDo you want to save anyway?\n(This text will be lost)"
            result = messagebox.askyesno("Unadded Items", message, icon='warning')
            if not result:
                return  # User cancelled
        
        # Update config with default values
        self.ui.config["handler_name"] = sv.default_handler.get()
        self.ui.config["db_type"] = sv.db_type.get()
        
        # Save config file
        self.ui.save_config()
        
        # Save machine-specific paths
        self.ui.machine_db_path = sv.db_path.get()
        self.ui.machine_trail_maps_folder = sv.trail_maps_folder.get()
        self.ui.machine_backup_folder = sv.backup_folder.get()
        self.ui.save_bootstrap()
        
        # Save settings backup JSON file
        self.ui.misc_data_ops.save_settings_backup()
        
        # Take new snapshot after saving
        self.ui.form_mgmt.take_form_snapshot()
        
        sv.status.set("Configuration saved successfully!")
        messagebox.showinfo("Success", "Configuration saved successfully!")
    

