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
import shutil
from datetime import datetime
from getpass import getuser
from sqlalchemy import text
import sv  # Import centralized StringVars module
from ui_database import DatabaseOperations
from ui_misc_data_ops import MiscDataOperations
from tips import ToolTip
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
        self.s_user_combo = None
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
        
        # =====================================================================
        # DATABASE TYPE SELECTION - HIDDEN FOR NOW
        # SQLite is used by default. Multi-database support may be re-enabled
        # in a future version once networking issues are resolved.
        # =====================================================================
        # Ensure SQLite is set as default
        sv.db_type.set("sqlite")
        
        # Hidden: Database Type Selection
        # db_type_frame = tk.LabelFrame(frame, text="Database Type", padx=10, pady=5)
        # db_type_frame.pack(fill="x", pady=5)
        # ... (Database type radio buttons and password fields hidden)
        # =====================================================================
        
        # Primary Storage Folder (renamed from "Database Folder")
        db_frame = tk.LabelFrame(frame, text="Primary Storage Folder", padx=10, pady=5)
        db_frame.pack(fill="x", pady=5)
        
        primary_entry = tk.Entry(db_frame, textvariable=sv.db_path, width=70)
        primary_entry.pack(side="left", padx=5)
        ToolTip(primary_entry, 
                "This folder contains the database as well as needed folders\n"
                "for ancillary data such as images and primary backup for\n"
                "error recovery.")
        # Add FocusOut handler to validate typed paths
        primary_entry.bind('<FocusOut>', lambda e: self._validate_typed_path('primary'))
        
        tk.Button(db_frame, text="Browse", command=self.ui.file_ops.select_db_folder).pack(side="left", padx=5)
        self.s_create_db_btn = tk.Button(db_frame, text="Initialize Data Structures", 
                                       command=self.initialize_data_structures, state="disabled")
        self.s_create_db_btn.pack(side="left", padx=5)
        
        # User selection combobox
        tk.Label(db_frame, text="User:").pack(side="left", padx=(15, 2))
        self.s_user_combo = ttk.Combobox(db_frame, textvariable=sv.current_user, width=15)
        self.s_user_combo['values'] = self.ui.machine_user_list if self.ui.machine_user_list else []
        self.s_user_combo.pack(side="left", padx=2)
        ToolTip(self.s_user_combo,
                "Select an existing user or type a new username.\n"
                "Each user has their own storage folder configuration.\n"
                "Changing users requires application restart to take effect.")
        
        # Bind FocusOut to handle user selection/creation
        self.s_user_combo.bind('<FocusOut>', self._on_user_combo_focus_out)
        
        # Add trace to db_path to enable/disable Initialize button
        sv.db_path.trace_add('write', self.update_create_db_button_state)
        
        # Initialize button state
        self.ui.root.after(100, self.update_create_db_button_state)
        
        # Secondary Backup Folder
        backup_frame = tk.LabelFrame(frame, text="Secondary Backup Folder", padx=10, pady=5)
        backup_frame.pack(fill="x", pady=5)
        
        secondary_entry = tk.Entry(backup_frame, textvariable=sv.backup_folder, width=70)
        secondary_entry.pack(side="left", padx=5)
        ToolTip(secondary_entry, 
                "Optional secondary backup location on a different drive.\n"
                "All writes to the Primary Storage Folder's JSON and Images\n"
                "subfolders are automatically mirrored here for redundancy.")
        # Add FocusOut handler to validate typed paths
        secondary_entry.bind('<FocusOut>', lambda e: self._validate_typed_path('secondary'))
        
        tk.Button(backup_frame, text="Browse", command=self.ui.file_ops.select_backup_folder).pack(side="left", padx=5)
        tk.Button(backup_frame, text="Restore from Secondary Backup", 
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
        
        tk.Button(save_config_frame, text="Save Configuration",
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
            self.ui.save_bootstrap()

    
    def select_folder(self):
        """Select trail maps folder"""
        folder = filedialog.askdirectory(title="Select Trail Maps Storage Folder")
        if folder:
            sv.trail_maps_folder.set(folder)
            self.ui.machine_trail_maps_folder = folder
            self.ui.save_bootstrap()

    def select_backup_folder(self):
        """Select backup folder"""
        folder = filedialog.askdirectory(title="Select Backup Folder")
        if folder:
            sv.backup_folder.set(folder)
            self.ui.machine_backup_folder = folder
            self.ui.save_bootstrap()

    def _validate_typed_path(self, path_type):
        """Validate a path that was typed (not browsed) and update bootstrap if needed.
        
        Args:
            path_type: 'primary', 'secondary', or 'trail_maps'
        """
        if path_type == 'primary':
            path_var = sv.db_path
            old_path = getattr(self.ui, 'machine_db_path', '') or ''
            attr_name = 'machine_db_path'
            label = "Primary Storage Folder"
        elif path_type == 'secondary':
            path_var = sv.backup_folder
            old_path = getattr(self.ui, 'machine_backup_folder', '') or ''
            attr_name = 'machine_backup_folder'
            label = "Secondary Backup Folder"
        elif path_type == 'trail_maps':
            path_var = sv.trail_maps_folder
            old_path = getattr(self.ui, 'machine_trail_maps_folder', '') or ''
            attr_name = 'machine_trail_maps_folder'
            label = "Trail Maps Folder"
        else:
            return
        
        new_path = path_var.get().strip()
        
        # No change or empty - do nothing
        if not new_path or new_path == old_path:
            return
        
        # Check if path exists
        folder_path = Path(new_path)
        if not folder_path.exists():
            # Ask if user wants to create it
            result = messagebox.askyesno(
                "Folder Does Not Exist",
                f"The {label} does not exist:\n\n{new_path}\n\n"
                "Would you like to create it?"
            )
            if result:
                try:
                    folder_path.mkdir(parents=True, exist_ok=True)
                    sv.status.set(f"Created folder: {new_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not create folder:\n{e}")
                    # Revert to old path
                    path_var.set(old_path)
                    return
            else:
                # User declined, revert to old path
                path_var.set(old_path)
                return
        
        # Path exists or was created - ask if user wants to update
        result = messagebox.askyesno(
            "Update Folder Location",
            f"Do you want to update the {label} to:\n\n{new_path}\n\n"
            "This will update the bootstrap configuration file."
        )
        
        if result:
            # Update the machine attribute
            setattr(self.ui, attr_name, new_path)
            
            # Save bootstrap file
            self.ui.save_bootstrap()
            sv.status.set(f"Updated {label} and saved bootstrap")
        else:
            # Revert to old path
            path_var.set(old_path)

    def update_create_db_button_state(self, *args):
        """Enable/disable Initialize Data Structures button based on folder selection"""
        has_folder = bool(sv.db_path.get().strip())
        if self.s_create_db_btn:
            self.s_create_db_btn.config(state="normal" if has_folder else "disabled")

    def initialize_data_structures(self):
        """Initialize primary storage folder with database and required subfolders.
        
        Creates:
        - air_scenting.db (SQLite database)
        - Images/ folder (for trail maps and images)
        - JSON/ folder (for backup data)
        
        If folder contains existing data, offers to move it to a Recover subfolder.
        """
        folder = sv.db_path.get().strip()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a Primary Storage Folder first")
            return
        
        folder_path = Path(folder)
        if not folder_path.exists():
            messagebox.showerror("Invalid Folder", f"Folder does not exist:\n{folder}")
            return
        
        # Define paths for data structures
        db_path = folder_path / "air_scenting.db"
        images_path = folder_path / "Images"
        json_path = folder_path / "JSON"
        
        # Check what already exists
        db_exists = db_path.exists()
        images_exists = images_path.exists()
        json_exists = json_path.exists()
        
        # Check for any other files in the folder (excluding our structures)
        existing_files = []
        for item in folder_path.iterdir():
            if item.name not in ["air_scenting.db", "air_scenting.db-wal", "air_scenting.db-shm", 
                                 "Images", "JSON", "Recover"]:
                existing_files.append(item.name)
        
        has_existing_data = db_exists or images_exists or json_exists or existing_files
        
        if has_existing_data:
            # Build message about what exists
            exists_list = []
            if db_exists:
                exists_list.append("Database (air_scenting.db)")
            if images_exists:
                exists_list.append("Images folder")
            if json_exists:
                exists_list.append("JSON folder")
            if existing_files:
                exists_list.append(f"Other files: {', '.join(existing_files[:5])}")
                if len(existing_files) > 5:
                    exists_list.append(f"  ...and {len(existing_files) - 5} more")
            
            result = messagebox.askyesno(
                "Folder Not Empty",
                f"Folder {folder} is not empty.\n\n"
                f"Existing data found:\n" + "\n".join(f"  - {item}" for item in exists_list) + "\n\n"
                "Really continue?\n\n"
                "If you select 'Yes', existing data will be moved to a 'Recover' subfolder.",
                icon='warning'
            )
            
            if not result:
                return
            
            # Move existing data to Recover folder
            recover_path = folder_path / "Recover"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recover_subfolder = recover_path / timestamp
            
            try:
                recover_subfolder.mkdir(parents=True, exist_ok=True)
                
                moved_items = []
                
                # Close any existing database connections first
                try:
                    from database import engine
                    engine.dispose()
                    import gc
                    gc.collect()
                    import time
                    time.sleep(0.5)
                except:
                    pass
                
                # Move database files
                if db_exists:
                    shutil.move(str(db_path), str(recover_subfolder / "air_scenting.db"))
                    moved_items.append("air_scenting.db")
                # Move WAL files if they exist
                wal_file = folder_path / "air_scenting.db-wal"
                shm_file = folder_path / "air_scenting.db-shm"
                if wal_file.exists():
                    shutil.move(str(wal_file), str(recover_subfolder / "air_scenting.db-wal"))
                if shm_file.exists():
                    shutil.move(str(shm_file), str(recover_subfolder / "air_scenting.db-shm"))
                
                # Move Images folder
                if images_exists:
                    shutil.move(str(images_path), str(recover_subfolder / "Images"))
                    moved_items.append("Images/")
                
                # Move JSON folder
                if json_exists:
                    shutil.move(str(json_path), str(recover_subfolder / "JSON"))
                    moved_items.append("JSON/")
                
                # Move other files
                for filename in existing_files:
                    src = folder_path / filename
                    if src.exists():
                        shutil.move(str(src), str(recover_subfolder / filename))
                        moved_items.append(filename)
                
                sv.status.set(f"Moved {len(moved_items)} item(s) to Recover folder")
                
                # Notify user
                messagebox.showinfo(
                    "Data Moved to Recover",
                    f"Existing data has been moved to:\n\n"
                    f"{recover_subfolder}\n\n"
                    f"Items moved: {', '.join(moved_items)}"
                )
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to move existing data:\n{e}")
                return
        
        # Now create the data structures
        try:
            # Create Images folder in primary
            images_path.mkdir(exist_ok=True)
            
            # Create JSON folder in primary
            json_path.mkdir(exist_ok=True)
            
            # Set trail_maps_folder to point to primary Images folder
            # (This is used internally even though the UI field was removed)
            sv.trail_maps_folder.set(str(images_path))
            
            # Also update machine-specific paths for bootstrap saving
            self.ui.machine_db_path = folder
            self.ui.machine_trail_maps_folder = str(images_path)
            # Note: machine_backup_folder stays as the secondary backup path
            
            # Create the database
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.close()
            
            # Update config to point to the new database
            import config
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
            
            sv.status.set(f"Initialized: database, Images/, JSON/ in {folder}")
            
            # Set up secondary backup folder if specified
            secondary_folder = sv.backup_folder.get().strip()
            if secondary_folder:
                self._setup_secondary_backup_folder(secondary_folder)
            
            # Offer to restore from JSON backups if they exist in JSON folder
            self.ui.misc_data_ops.restore_from_json_backups("sqlite")
            
            # Offer to load default terrain and distraction types
            self.ui.misc_data_ops.offer_load_default_types("sqlite")
            
            # Update session number and UI
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
            self.ui.form_mgmt.update_subjects_found()
            
            # Refresh Setup tab lists
            self.refresh_dog_list()
            self.load_locations_from_database()
            self.load_terrain_from_database()
            self.load_distraction_from_database()
            
            # Save configuration and bootstrap to persist the new paths
            self.ui.save_config()
            self.ui.save_bootstrap()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize data structures:\n{e}\n\n{type(e).__name__}")
            import traceback
            traceback.print_exc()
    
    def _setup_secondary_backup_folder(self, secondary_folder):
        """Set up the secondary backup folder structure.
        
        Creates Images/ and JSON/ subfolders in the secondary backup location.
        If folders already exist, warns but doesn't remove anything.
        
        Args:
            secondary_folder: Path to the secondary backup folder
        """
        secondary_path = Path(secondary_folder)
        
        if not secondary_path.exists():
            messagebox.showerror("Invalid Folder", 
                f"Secondary backup folder does not exist:\n{secondary_folder}")
            return
        
        secondary_images = secondary_path / "Images"
        secondary_json = secondary_path / "JSON"
        
        # Check what already exists and has files
        images_exists = secondary_images.exists()
        json_exists = secondary_json.exists()
        images_has_files = images_exists and any(secondary_images.iterdir())
        json_has_files = json_exists and any(secondary_json.iterdir())
        
        if images_has_files or json_has_files:
            exists_list = []
            if images_has_files:
                exists_list.append("Images/")
            if json_has_files:
                exists_list.append("JSON/")
            
            messagebox.showinfo(
                "Secondary Backup Folder",
                f"Secondary backup folder already has data:\n\n"
                f"Found files in: {', '.join(exists_list)}\n\n"
                f"Existing files will be preserved.\n"
                f"New backups will be added to these folders."
            )
        
        # Create folders if they don't exist
        try:
            secondary_images.mkdir(exist_ok=True)
            secondary_json.mkdir(exist_ok=True)
            print(f"Created/verified secondary backup folders:")
            print(f"  Images: {secondary_images} (exists={secondary_images.exists()})")
            print(f"  JSON: {secondary_json} (exists={secondary_json.exists()})")
            
            # Update machine-specific path for bootstrap
            self.ui.machine_backup_folder = secondary_folder
            
            sv.status.set(f"Secondary backup initialized at {secondary_folder}")
            
        except Exception as e:
            messagebox.showerror("Error", 
                f"Failed to create secondary backup folders:\n{e}")

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
                
                # Refresh Setup tab lists (new database has no data initially, but offer_load_default_types may have added some)
                self.refresh_dog_list()
                self.load_locations_from_database()
                self.load_terrain_from_database()
                self.load_distraction_from_database()
                
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
                
                # Refresh Setup tab lists
                self.refresh_dog_list()
                self.load_locations_from_database()
                self.load_terrain_from_database()
                self.load_distraction_from_database()
                
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
                if hasattr(self.ui, 'a_location_combo') and self.ui.a_location_combo:
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
            if hasattr(self.ui, 'a_location_combo') and self.ui.a_location_combo:
                self.ui.a_location_combo['values'] = locations
            
            # Update trailing location combo if available
            if hasattr(self.ui, 'trailing_entry') and hasattr(self.ui.trailing_entry, 'update_location_list'):
                self.ui.trailing_entry.update_location_list(locations)
                
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
                if hasattr(self.ui, 'a_location_combo') and self.ui.a_location_combo:
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
            if hasattr(self.ui, 'a_terrain_combo') and self.ui.a_terrain_combo:
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
                
                # Sync config with database and save
                self._sync_config_from_database()
                
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
                
                # Sync config with database and save
                self._sync_config_from_database()
                
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
                if hasattr(self.ui, 'a_dog_combo') and self.ui.a_dog_combo:
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
            if hasattr(self.ui, 'a_dog_combo') and self.ui.a_dog_combo:
                self.ui.a_dog_combo['values'] = dogs
            
            # Update trailing dog combo if available
            if hasattr(self.ui, 'trailing_entry') and self.ui.trailing_entry:
                if hasattr(self.ui.trailing_entry, 'update_dog_list'):
                    self.ui.trailing_entry.update_dog_list(dogs)
            
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
                if hasattr(self.ui, 'a_dog_combo') and self.ui.a_dog_combo:
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
            
            old_db_type = None
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
                
                # Refresh dog lists in all tabs (airscenting and trailing)
                self.refresh_dog_list()
                
                # Select the newly added dog in the combobox
                sv.dog.set(dog_name)
                
                sv.new_dog.set("")
                sv.status.set(f"Added dog: {dog_name}")
                
                # Sync config with database and save
                self._sync_config_from_database()
                
            except Exception as e:
                # Restore original DB_TYPE on error
                if old_db_type is not None:
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
                if hasattr(self.ui, 'a_dog_combo') and self.ui.a_dog_combo:
                    self.refresh_dog_list()
                
                sv.status.set(f"Removed dog: {dog_name}")
                self.s_remove_dog_btn.config(state="disabled")
                
                # Sync config with database and save
                self._sync_config_from_database()
                
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
                
                # Sync config with database and save
                self._sync_config_from_database()
                
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
                
                # Sync config with database and save
                self._sync_config_from_database()
                
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
                
                # Save config
                self.ui.save_config()

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
                
                # Save config
                self.ui.save_config()

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
            
            # Save config
            self.ui.save_config()
    

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
                
                # Sync config with database and save
                self._sync_config_from_database()
                
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
                
                # Sync config with database and save
                self._sync_config_from_database()
                
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
                
                # Save config
                self.ui.save_config()

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
                
                # Save config
                self.ui.save_config()

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
            
            # Save config
            self.ui.save_config()
    

    def save_configuration_settings(self):
        """Save all configuration settings including data from database"""
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
        
        # Ensure airscenting section exists
        if "airscenting" not in self.ui.config:
            self.ui.config["airscenting"] = {}
        
        # Update config with default values (nested under airscenting)
        self.ui.config["airscenting"]["default_handler"] = sv.default_handler.get()
        self.ui.config["db_type"] = sv.db_type.get()
        
        # Get current data from database and store in config for backup/rebuild
        try:
            from ui_database import get_db_manager
            db_mgr = get_db_manager(sv.db_type.get())
            
            # Get dog names from database
            dog_names = db_mgr.load_dogs()
            self.ui.config["dog_names"] = dog_names if dog_names else []
            
            # Get terrain types from database
            terrain_types = db_mgr.load_terrain_types()
            self.ui.config["terrain_types"] = terrain_types if terrain_types else []
            
            # Get distraction types from database
            distraction_types = db_mgr.load_distraction_types()
            self.ui.config["distraction_types"] = distraction_types if distraction_types else []
            
            # Get training locations from database
            locations = db_mgr.load_locations()
            self.ui.config["training_locations"] = locations if locations else []
            
        except Exception as e:
            print(f"Warning: Could not load data from database for config: {e}")
        
        # Save machine-specific paths first (so JSON folder path is known)
        self.ui.machine_db_path = sv.db_path.get()
        self.ui.machine_trail_maps_folder = sv.trail_maps_folder.get()
        self.ui.machine_backup_folder = sv.backup_folder.get()
        self.ui.save_bootstrap()
        
        # Save config file (will use JSON folder if available)
        self.ui.save_config()
        
        # Save settings backup JSON file
        self.ui.misc_data_ops.save_settings_backup()
        
        # Take new snapshot after saving
        self.ui.form_mgmt.take_form_snapshot()
        
        sv.status.set("Configuration saved successfully!")
    
    def _sync_config_from_database(self):
        """Sync config with current database data and save to file.
        
        Called after any add/remove/move operation on dogs, locations,
        terrain types, or distraction types.
        """
        try:
            from ui_database import get_db_manager
            db_mgr = get_db_manager(sv.db_type.get())
            
            # Get dog names from database
            dog_names = db_mgr.load_dogs()
            self.ui.config["dog_names"] = dog_names if dog_names else []
            
            # Get terrain types from database
            terrain_types = db_mgr.load_terrain_types()
            self.ui.config["terrain_types"] = terrain_types if terrain_types else []
            
            # Get distraction types from database
            distraction_types = db_mgr.load_distraction_types()
            self.ui.config["distraction_types"] = distraction_types if distraction_types else []
            
            # Get training locations from database
            locations = db_mgr.load_locations()
            self.ui.config["training_locations"] = locations if locations else []
            
            # Save config to file
            self.ui.save_config()
            
        except Exception as e:
            print(f"Warning: Could not sync config from database: {e}")
    
    def _on_user_combo_focus_out(self, event=None):
        """Handle user combobox focus out - save new user and prompt for restart.
        
        When user types a new username or selects an existing one:
        1. If new user: Add to bootstrap, save, prompt for restart
        2. If existing user different from current: Prompt for restart
        3. If same user: No action needed
        """
        new_user = sv.current_user.get().strip()
        
        if not new_user:
            # Empty username - restore to current user
            sv.current_user.set(self.ui.machine_current_user)
            return
        
        # Check if user changed
        if new_user == self.ui.machine_current_user:
            # No change
            return
        
        # Check if this is a new user or existing user
        is_new_user = new_user not in self.ui.machine_user_list
        
        if is_new_user:
            # New user - confirm creation
            result = messagebox.askyesno(
                "Create New User",
                f"Create new user '{new_user}'?\n\n"
                "This will save the current configuration and require\n"
                "an application restart to switch to the new user.\n\n"
                "The new user will start with empty storage folder settings."
            )
            
            if not result:
                # User cancelled - restore original
                sv.current_user.set(self.ui.machine_current_user)
                return
            
            # Add new user to bootstrap with empty settings
            self._add_new_user_to_bootstrap(new_user)
            
            # Update combo values
            self.s_user_combo['values'] = self.ui.machine_user_list
            
            # Prompt for restart
            messagebox.showinfo(
                "Restart Required",
                f"User '{new_user}' has been created.\n\n"
                "Please restart the application to switch to this user.\n\n"
                "The application will now continue with the current user."
            )
            
            # Restore current user (change takes effect on restart)
            sv.current_user.set(self.ui.machine_current_user)
        else:
            # Existing user - prompt for restart to switch
            result = messagebox.askyesno(
                "Switch User",
                f"Switch to user '{new_user}'?\n\n"
                "This requires an application restart to take effect."
            )
            
            if not result:
                # User cancelled - restore original
                sv.current_user.set(self.ui.machine_current_user)
                return
            
            # Update bootstrap with new current user
            self._set_current_user_in_bootstrap(new_user)
            
            # Prompt for restart
            messagebox.showinfo(
                "Restart Required",
                f"User will be switched to '{new_user}' on next startup.\n\n"
                "Please restart the application to apply the change.\n\n"
                "The application will now continue with the current user."
            )
            
            # Restore current user (change takes effect on restart)
            sv.current_user.set(self.ui.machine_current_user)
    
    def _add_new_user_to_bootstrap(self, username):
        """Add a new user to the bootstrap file with empty settings.
        
        Args:
            username: The new username to add
        """
        import json
        from config import BOOTSTRAP_FILE
        
        # Load existing bootstrap
        bootstrap = {"current_user": "", "users": {}}
        if BOOTSTRAP_FILE.exists():
            try:
                with open(BOOTSTRAP_FILE, 'r') as f:
                    existing = json.load(f)
                    
                    # Handle legacy format migration
                    if "users" in existing:
                        bootstrap = existing
                    else:
                        # Migrate legacy format
                        default_user = getuser()
                        bootstrap["current_user"] = existing.get("current_user", default_user)
                        bootstrap["users"][default_user] = {
                            "db_file_path": existing.get("db_file_path", ""),
                            "trail_maps_folder": existing.get("trail_maps_folder", ""),
                            "backup_folder": existing.get("backup_folder", "")
                        }
            except:
                pass
        
        # Ensure users dict exists
        if "users" not in bootstrap:
            bootstrap["users"] = {}
        
        # Add new user with empty settings
        if username not in bootstrap["users"]:
            bootstrap["users"][username] = {
                "db_file_path": "",
                "trail_maps_folder": "",
                "backup_folder": ""
            }
        
        # Set as current user (will take effect on restart)
        bootstrap["current_user"] = username
        
        # Save bootstrap
        with open(BOOTSTRAP_FILE, 'w') as f:
            json.dump(bootstrap, f, indent=2)
        
        # Update machine user list
        self.ui.machine_user_list = list(bootstrap["users"].keys())
    
    def _set_current_user_in_bootstrap(self, username):
        """Set the current user in bootstrap file (for restart).
        
        Args:
            username: The username to set as current
        """
        import json
        from config import BOOTSTRAP_FILE
        
        # Load existing bootstrap
        bootstrap = {"current_user": "", "users": {}}
        if BOOTSTRAP_FILE.exists():
            try:
                with open(BOOTSTRAP_FILE, 'r') as f:
                    existing = json.load(f)
                    
                    # Handle legacy format migration
                    if "users" in existing:
                        bootstrap = existing
                    else:
                        # Migrate legacy format
                        default_user = getuser()
                        bootstrap["current_user"] = existing.get("current_user", default_user)
                        bootstrap["users"][default_user] = {
                            "db_file_path": existing.get("db_file_path", ""),
                            "trail_maps_folder": existing.get("trail_maps_folder", ""),
                            "backup_folder": existing.get("backup_folder", "")
                        }
            except:
                pass
        
        # Ensure users dict exists
        if "users" not in bootstrap:
            bootstrap["users"] = {}
        
        # Set current user
        bootstrap["current_user"] = username
        
        # Save bootstrap
        with open(BOOTSTRAP_FILE, 'w') as f:
            json.dump(bootstrap, f, indent=2)
