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
Miscellaneous Data Operations for Air-Scenting Logger UI
Handles initialization, backups, restore, and default data loading
"""
import os
import json
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
from ui_utils import get_username, get_default_terrain_types, get_default_distraction_types
from ui_database import DatabaseOperations, get_db_manager
from working_dialog import WorkingDialog
import sv


class MiscDataOperations:
    """Handles miscellaneous data operations: initialization, backups, restore"""
    
    def __init__(self, ui):
        """Initialize with reference to main UI"""
        self.ui = ui
    
    def validate_database_at_startup(self):
        """
        Check if database exists and is valid at startup.
        If database is missing or corrupted, offer to rebuild from JSON backups.
        
        Returns:
            bool: True if database is valid or was successfully rebuilt, False otherwise
        """
        import config
        
        # Get the primary storage folder path
        db_folder = sv.db_path.get().strip()
        if not db_folder:
            # No folder configured - user needs to run setup
            return False
        
        folder_path = Path(db_folder)
        if not folder_path.exists():
            return False
        
        db_path = folder_path / "air_scenting.db"
        json_path = folder_path / "JSON"
        
        # Check if database exists
        if not db_path.exists():
            # Database missing - check for JSON backups
            return self._offer_rebuild_from_json(db_path, json_path, "Database file not found.")
        
        # Database file exists - check if it's valid using PRAGMA integrity_check
        try:
            import sqlite3
            
            # Use sqlite3 directly for integrity check (more reliable than SQLAlchemy for this)
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result[0] != "ok":
                # Database is corrupted
                conn.close()
                return self._offer_rebuild_from_json(db_path, json_path, 
                    f"Database integrity check failed: {result[0]}")
            
            # Also verify the schema exists (tables created)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='training_sessions'")
            table_exists = cursor.fetchone()
            conn.close()
            
            if not table_exists:
                return self._offer_rebuild_from_json(db_path, json_path, 
                    "Database is missing required tables.")
            
            # Database is valid - now set up SQLAlchemy to use it
            config.DB_TYPE = "sqlite"
            config.DB_CONFIG["sqlite"]["url"] = f"sqlite:///{db_path}"
            
            # Reload database engine
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"Database validation error: {error_msg}")
            
            # Database exists but is corrupted or inaccessible
            return self._offer_rebuild_from_json(db_path, json_path, f"Database error: {error_msg}")
    
    def _offer_rebuild_from_json(self, db_path, json_path, reason):
        """
        Offer to rebuild database from JSON backup files.
        
        Args:
            db_path: Path to database file
            json_path: Path to JSON backup folder
            reason: Reason why rebuild is needed
            
        Returns:
            bool: True if database was rebuilt successfully, False otherwise
        """
        # Check if JSON backup folder exists and has files
        if not json_path.exists():
            messagebox.showwarning(
                "No Database",
                f"{reason}\n\n"
                f"No JSON backup folder found at:\n{json_path}\n\n"
                "Please use Setup tab to initialize data structures."
            )
            return False
        
        json_files = list(json_path.glob("*session_*.json"))
        config_file = json_path / ".training_log_config.json"
        has_config = config_file.exists()
        
        if not json_files and not has_config:
            messagebox.showwarning(
                "No Database",
                f"{reason}\n\n"
                f"No backup files found in:\n{json_path}\n\n"
                "Please use Setup tab to initialize data structures."
            )
            return False
        
        # Build message about what can be restored
        restore_items = []
        if json_files:
            restore_items.append(f"{len(json_files)} session backup file(s)")
        if has_config:
            restore_items.append("configuration data (dogs, terrains, locations)")
        
        # Offer to rebuild
        result = messagebox.askyesno(
            "Rebuild Database?",
            f"{reason}\n\n"
            f"Found in {json_path}:\n" + "\n".join(f"  â€¢ {item}" for item in restore_items) + "\n\n"
            "Would you like to rebuild the database from these backups?",
            icon='question'
        )
        
        if not result:
            return False
        
        # Rebuild the database
        try:
            # Delete corrupted database if it exists
            if db_path.exists():
                try:
                    from database import engine
                    engine.dispose()
                    import gc
                    gc.collect()
                    import time
                    time.sleep(0.5)
                    db_path.unlink()
                    # Also delete WAL files
                    wal_file = Path(str(db_path) + "-wal")
                    shm_file = Path(str(db_path) + "-shm")
                    if wal_file.exists():
                        wal_file.unlink()
                    if shm_file.exists():
                        shm_file.unlink()
                except Exception as e:
                    messagebox.showerror("Error", f"Could not remove corrupted database:\n{e}")
                    return False
            
            # Create new database
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.close()
            
            # Update config
            import config
            config.DB_TYPE = "sqlite"
            config.DB_CONFIG["sqlite"]["url"] = f"sqlite:///{db_path}"
            
            # Reload database engine
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            # Create schema
            from schema import create_tables
            create_tables()
            
            sv.status.set("Database recreated, restoring from backups...")
            
            # Now restore from JSON backups (reuse existing logic but without asking)
            self._restore_sessions_from_json(json_path)
            
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rebuild database:\n{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _restore_sessions_from_json(self, json_path):
        """
        Restore sessions from JSON backup files (internal helper, no prompts).
        Also restores config data if available.
        
        Args:
            json_path: Path to JSON backup folder
        """
        import database
        
        json_files = list(json_path.glob("*session_*.json"))
        
        restored_count = 0
        failed_count = 0
        dog_names = set()
        location_names = set()
        
        # Restore sessions if any exist
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r') as f:
                    session_data = json.load(f)
                
                # Collect dog name
                dog_name = session_data.get('dog_name')
                if dog_name:
                    dog_names.add(dog_name)
                
                # Collect location name
                location = session_data.get('location')
                if location:
                    location_names.add(location)
                
                # Insert into database
                with database.get_connection() as conn:
                    image_files = session_data.get('image_files', [])
                    image_files_json = json.dumps(image_files) if isinstance(image_files, list) else (image_files or "")
                    
                    conn.execute(
                        text("""
                            INSERT INTO training_sessions 
                            (date, session_number, handler, session_purpose, field_support, dog_name, location,
                             search_area_size, num_subjects, handler_knowledge, weather, temperature, 
                             wind_direction, wind_speed, search_type, drive_level, subjects_found, 
                             comments, image_files, user_name)
                            VALUES (:date, :session_number, :handler, :session_purpose, :field_support, :dog_name, :location,
                                    :search_area_size, :num_subjects, :handler_knowledge, :weather, :temperature, 
                                    :wind_direction, :wind_speed, :search_type, :drive_level, :subjects_found,
                                    :comments, :image_files, :user_name)
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
                            "comments": session_data.get('comments'),
                            "image_files": image_files_json,
                            "user_name": session_data.get('user_name', get_username())
                        }
                    )
                    conn.commit()
                
                restored_count += 1
                
            except Exception as e:
                print(f"Failed to restore {json_file}: {e}")
                failed_count += 1
        
        # Add dog names to database
        for dog_name in sorted(dog_names):
            try:
                with database.get_connection() as conn:
                    conn.execute(
                        text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                        {"name": dog_name, "user_name": get_username()}
                    )
                    conn.commit()
            except:
                pass  # Duplicate OK
        
        # Add location names to database
        for location in sorted(location_names):
            try:
                with database.get_connection() as conn:
                    conn.execute(
                        text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                        {"name": location, "user_name": get_username()}
                    )
                    conn.commit()
            except:
                pass  # Duplicate OK
        
        # Also restore from config file if it exists
        config_restored = self._restore_config_data_to_db(json_path)
        
        sv.status.set(f"Restored {restored_count} session(s) from backup")
        if restored_count > 0 or config_restored:
            msg = f"Successfully restored {restored_count} session(s) from JSON backups."
            if config_restored:
                msg += "\n\nAlso restored configuration data (dogs, terrains, locations, distractions)."
            if failed_count > 0:
                msg += f"\n\n{failed_count} file(s) failed to restore."
            messagebox.showinfo("Database Rebuilt", msg)
    
    def _restore_config_data_to_db(self, json_path):
        """
        Restore configuration data (dogs, terrains, locations, distractions) from config file.
        
        Args:
            json_path: Path to JSON folder containing .training_log_config.json
            
        Returns:
            bool: True if config was restored, False otherwise
        """
        import database
        
        config_file = json_path / ".training_log_config.json"
        if not config_file.exists():
            return False
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except Exception as e:
            print(f"Could not load config file: {e}")
            return False
        
        restored_something = False
        
        # Restore dog names
        dog_names = config_data.get("dog_names", [])
        for dog_name in dog_names:
            if dog_name:
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                            {"name": dog_name, "user_name": get_username()}
                        )
                        conn.commit()
                    restored_something = True
                except:
                    pass  # Duplicate OK
        
        # Restore terrain types
        terrain_types = config_data.get("terrain_types", [])
        for i, terrain in enumerate(terrain_types):
            if terrain:
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO terrain_types (name, sort_order, user_name) VALUES (:name, :sort_order, :user_name)"),
                            {"name": terrain, "sort_order": i, "user_name": get_username()}
                        )
                        conn.commit()
                    restored_something = True
                except:
                    pass  # Duplicate OK
        
        # Restore distraction types
        distraction_types = config_data.get("distraction_types", [])
        for i, distraction in enumerate(distraction_types):
            if distraction:
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO distraction_types (name, sort_order, user_name) VALUES (:name, :sort_order, :user_name)"),
                            {"name": distraction, "sort_order": i, "user_name": get_username()}
                        )
                        conn.commit()
                    restored_something = True
                except:
                    pass  # Duplicate OK
        
        # Restore training locations
        locations = config_data.get("training_locations", [])
        for location in locations:
            if location:
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                            {"name": location, "user_name": get_username()}
                        )
                        conn.commit()
                    restored_something = True
                except:
                    pass  # Duplicate OK
        
        return restored_something

    def load_initial_database_data(self):
        """Load all initial database data after splash screen starts"""
        # Use chained after() calls to let event loop run between operations
        # This keeps splash countdown and progress bars animating
        
        # Disable View/Edit/Hide and Export PDF buttons until startup is complete
        self._disable_sync_sensitive_buttons()
        
        def step0():
            # First validate the database exists and is valid
            # This will offer to rebuild from JSON if needed
            if not self.validate_database_at_startup():
                # Database not valid and couldn't be rebuilt
                # Skip loading data, user needs to set up
                sv.status.set("Database not configured - please complete Setup")
                self._enable_sync_sensitive_buttons()  # Re-enable since we're done
                return
            
            # Check if database is healthy before deciding sync strategy
            db_healthy = self._check_db_health()
            
            if db_healthy:
                # DB is healthy - start sync in background thread
                self._start_startup_sync_thread()
            else:
                # DB appears damaged - run sync synchronously to rebuild
                print("Database appears damaged - running synchronous rebuild...")
                self._perform_synchronous_startup_sync()
                self._enable_sync_sensitive_buttons()
            
            self.ui.root.after(50, step1)
        
        def step1():
            self.ensure_db_ready()
            self.ui.load_locations_from_database()
            self.ui.root.after(50, step2)  # Schedule next step
        
        def step2():
            self.ui.load_dogs_from_database()
            self.ui.root.after(50, step3)
        
        def step3():
            self.ui.load_terrain_from_database()
            self.ui.root.after(50, step4)
        
        def step4():
            self.ui.load_distraction_from_database()
            self.ui.root.after(50, step5)
        
        def step5():
            # Load last selected dog from database
            try:
                last_dog = DatabaseOperations(self.ui).load_db_setting("last_dog_name", "")
                if last_dog:
                    sv.dog.set(last_dog)
                    # Update session number for this dog (on_dog_changed not triggered by programmatic set)
                    # Use computed next number based on filter (Airscent sessions only)
                    status_filter = sv.session_status_filter.get()
                    filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(
                        last_dog, status_filter, entry_type="Airscent"
                    )
                    next_computed = len(filtered_sessions) + 1
                    sv.session_number.set(str(next_computed))
            except Exception as e:
                print(f"Could not load last dog: {e}")
            self.ui.root.after(50, step6)
        
        def step6():
            # Refresh Entry tab comboboxes if they exist
            if hasattr(self.ui, 'a_dog_combo'):
                self.ui.refresh_dog_list()
            self.ui.root.after(50, step7)
        
        def step7():
            if hasattr(self.ui, 'a_location_combo'):
                self.ui.refresh_location_list()
            self.ui.root.after(50, step8)
        
        def step8():
            if hasattr(self.ui, 'a_terrain_combo'):
                self.ui.refresh_terrain_list()
            self.ui.root.after(50, step9)
        
        def step9():
            # Update navigation buttons now that dog and session are loaded
            if hasattr(self.ui, 'a_prev_session_btn'):
                self.ui.navigation.update_navigation_buttons()
            self.ui.root.after(100, step10)
        
        def step10():
            # Sync was already started in step0
            # Buttons will be re-enabled when sync thread completes
            
            # Select Entry tab since database is valid
            # (We only get here if validate_database_at_startup returned True)
            if hasattr(self.ui, 'notebook') and hasattr(self.ui, 'entry_tab'):
                self.ui.notebook.select(self.ui.entry_tab)
                print("Database valid - starting on Entry tab")
        
        # Start the chain with database validation
        step0()
    
    def _disable_sync_sensitive_buttons(self):
        """Disable buttons that shouldn't be used during sync."""
        import tkinter as tk
        sv.sync_in_progress = True
        if hasattr(self.ui, 'a_edit_delete_btn'):
            self.ui.a_edit_delete_btn.config(state=tk.DISABLED)
        if hasattr(self.ui, 'a_export_pdf_btn'):
            self.ui.a_export_pdf_btn.config(state=tk.DISABLED)
    
    def _enable_sync_sensitive_buttons(self):
        """Re-enable buttons after sync completes."""
        import tkinter as tk
        sv.sync_in_progress = False
        if hasattr(self.ui, 'a_edit_delete_btn'):
            self.ui.a_edit_delete_btn.config(state=tk.NORMAL)
        if hasattr(self.ui, 'a_export_pdf_btn'):
            self.ui.a_export_pdf_btn.config(state=tk.NORMAL)
    
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
                        sv.status.set(message)
                    self.ui.root.after(0, update)
                
                results = sync_manager.perform_full_sync(status_callback=status_callback)
                
                def on_complete():
                    # Re-enable buttons
                    self._enable_sync_sensitive_buttons()
                    
                    # Update session number if DB was updated
                    db_updates = results.get('db_updates', 0)
                    if db_updates > 0:
                        dog_name = sv.dog.get()
                        if dog_name:
                            try:
                                from ui_database import DatabaseOperations
                                status_filter = sv.session_status_filter.get()
                                filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(
                                    dog_name, status_filter, entry_type="Airscent"
                                )
                                next_computed = len(filtered_sessions) + 1
                                sv.session_number.set(str(next_computed))
                                print(f"Startup sync: Updated session number to {next_computed} for {dog_name}")
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
                        sv.status.set(f"Sync complete: {total_changes} file(s) synchronized")
                    else:
                        sv.status.set("Ready")
                
                self.ui.root.after(0, on_complete)
                
            except Exception as e:
                print(f"Startup sync error: {e}")
                import traceback
                traceback.print_exc()
                
                def reset():
                    self._enable_sync_sensitive_buttons()
                    sv.status.set("Ready")
                self.ui.root.after(0, reset)
        
        # Start sync thread
        sync_thread = threading.Thread(target=do_sync, daemon=True)
        sync_thread.start()
        print("Startup sync: Started in background thread")
    
    def _perform_synchronous_startup_sync(self):
        """Perform startup sync synchronously (blocking) for DB rebuild."""
        try:
            from backup_sync import BackupSyncManager
            from ui_utils import get_primary_json_folder, get_secondary_json_folder
            
            db_type = sv.db_type.get()
            primary_folder = get_primary_json_folder()
            secondary_folder = get_secondary_json_folder()
            
            if not primary_folder:
                print("Startup sync: No primary JSON folder configured, skipping")
                return
            
            print("Startup sync: Beginning synchronous synchronization...")
            sv.status.set("Rebuilding database from backups...")
            self.ui.root.update_idletasks()
            
            sync_manager = BackupSyncManager(
                db_type=db_type,
                primary_folder=primary_folder,
                secondary_folder=secondary_folder
            )
            
            def status_callback(message):
                print(f"  {message}")
                sv.status.set(message)
                self.ui.root.update_idletasks()
            
            results = sync_manager.perform_full_sync(status_callback=status_callback)
            
            total_changes = (
                results.get('db_updates', 0) +
                results.get('primary_writes', 0) +
                results.get('secondary_writes', 0) +
                results.get('renames', 0)
            )
            
            if total_changes > 0:
                print(f"Startup sync complete: {total_changes} change(s)")
                sv.status.set(f"Rebuild complete: {total_changes} file(s) synchronized")
            else:
                print("Startup sync complete: All backups already in sync")
                sv.status.set("Ready")
            
        except Exception as e:
            print(f"Startup sync error: {e}")
            import traceback
            traceback.print_exc()
    
    def _start_background_sync(self):
        """Start background sync between database and JSON backup folders.
        
        Uses the new backup_sync module for comprehensive synchronization
        with checksum tracking and proper conflict resolution.
        
        Note: Buttons are already disabled by load_initial_database_data.
        This method will re-enable them when sync completes.
        """
        import threading
        from ui_utils import get_primary_json_folder, get_secondary_json_folder
        
        try:
            db_type = sv.db_type.get()
            primary_folder = get_primary_json_folder()
            secondary_folder = get_secondary_json_folder()
            
            if not primary_folder:
                print("Sync: No primary JSON folder configured, skipping sync")
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
                            sv.status.set(message)
                        self.ui.root.after(0, update)
                    
                    results = sync_manager.perform_full_sync(status_callback=status_callback)
                    
                    def update_ui():
                        # Re-enable buttons
                        self._enable_sync_sensitive_buttons()
                        
                        # Update session number if sessions were added
                        db_updates = results.get("db_updates", 0)
                        if db_updates > 0:
                            # Recalculate session number for current dog
                            dog_name = sv.dog.get()
                            if dog_name:
                                try:
                                    from ui_database import DatabaseOperations
                                    status_filter = sv.session_status_filter.get()
                                    filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(
                                        dog_name, status_filter, entry_type="Airscent"
                                    )
                                    next_computed = len(filtered_sessions) + 1
                                    sv.session_number.set(str(next_computed))
                                    print(f"Sync: Updated session number to {next_computed} for {dog_name}")
                                except Exception as e:
                                    print(f"Sync: Error updating session number: {e}")
                        
                        # Build status message
                        total_changes = (
                            db_updates +
                            results.get('primary_writes', 0) +
                            results.get('secondary_writes', 0) +
                            results.get('renames', 0)
                        )
                        
                        if total_changes > 0:
                            sv.status.set(f"Sync complete: {total_changes} file(s) synchronized")
                        else:
                            sv.status.set("Sync complete: All backups up to date")
                        
                        if results.get('errors'):
                            print(f"Sync errors: {results['errors']}")
                    
                    self.ui.root.after(0, update_ui)
                    
                except Exception as e:
                    print(f"Background sync error: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    def reset_ui():
                        self._enable_sync_sensitive_buttons()
                    self.ui.root.after(0, reset_ui)
            
            # Start sync thread
            sync_thread = threading.Thread(target=do_sync, daemon=True)
            sync_thread.start()
            
            print("Sync: Background sync started")
            
        except Exception as e:
            print(f"Error starting background sync: {e}")
            self._enable_sync_sensitive_buttons()
    
    def select_initial_tab(self):
        """Select initial tab based on database existence"""
        db_type = sv.db_type.get()
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
            self.ui.notebook.select(self.ui.entry_tab)
            self.ui.previous_tab_index = 1  # Update to reflect we're on Entry tab
        else:
            # No database - show Setup tab (already default)
            self.ui.notebook.select(self.ui.setup_tab)
            self.ui.previous_tab_index = 0
    
    def save_session_to_json(self, session_data):
        """Save session data to JSON backup file in both primary and secondary locations.
        
        Uses consistent naming: a_{user}_{dog}_{session_number}.json
        Updates database with checksum and file timestamps.
        """
        import re
        from ui_utils import save_json_mirrored, get_secondary_json_folder
        
        try:
            # Get session info for filename (session_number from DB, not calculated)
            session_num = session_data.get('session_number')
            dog_name = session_data.get('dog_name', 'unknown')
            user_name = session_data.get('user_name', '')
            
            # Sanitize names for filename (remove special characters)
            safe_user_name = re.sub(r'[^\w\-]', '_', user_name) if user_name else 'unknown'
            safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
            
            # Consistent naming convention: a_{user}_{dog}_{session}.json
            filename = f"a_{safe_user_name}_{safe_dog_name}_{session_num}.json"
            
            # Add timestamp to data
            session_data['update_time'] = datetime.now().isoformat()
            
            # Save to both primary and secondary (returns checksum and timestamps)
            primary, secondary, checksum, primary_ts, secondary_ts = save_json_mirrored(filename, session_data)
            
            if primary:
                print(f"Session backup saved: {primary}")
            if secondary:
                print(f"Session backup mirrored: {secondary}")
            
            # Update database with checksum and timestamps
            if checksum:
                try:
                    self._update_session_backup_info(session_num, dog_name, checksum, primary_ts, secondary_ts)
                except Exception as e:
                    print(f"Warning: Could not update backup info in DB: {e}")
            
            # Check if secondary backup was configured but unavailable
            # Notify user once per session via status bar
            if not secondary and sv.backup_folder.get().strip():
                if not sv.secondary_unavailable_notified:
                    sv.secondary_unavailable_notified = True
                    sv.status.set("Warning: Secondary backup folder unavailable - backup saved to primary only")
                    
        except Exception as e:
            error_msg = f"Backup failed: {str(e)}"
            print(f"Warning: Failed to save session to JSON: {e}")
            self.ui.show_status_message(error_msg, "error")
    
    def _update_session_backup_info(self, session_number, dog_name, checksum, primary_ts, secondary_ts):
        """Update checksum and timestamps in database for a session."""
        try:
            from sqlalchemy import text
            from database import get_connection
            
            with get_connection() as conn:
                conn.execute(text("""
                    UPDATE training_sessions SET
                        checksum = :checksum,
                        primary_timestamp = :primary_ts,
                        secondary_timestamp = :secondary_ts
                    WHERE session_number = :session_number AND dog_name = :dog_name
                """), {
                    'checksum': checksum,
                    'primary_ts': primary_ts,
                    'secondary_ts': secondary_ts,
                    'session_number': session_number,
                    'dog_name': dog_name
                })
                conn.commit()
                print(f"Updated backup info: checksum={checksum[:16]}..., primary_ts={primary_ts}, secondary_ts={secondary_ts}")
        except Exception as e:
            print(f"Error updating session backup info: {e}")
    
    def save_settings_backup(self):
        """Save settings to JSON backup file in both primary and secondary locations.
        
        Uses the main config file which is already mirrored to secondary.
        """
        try:
            # The main config file already contains all settings and is mirrored
            # Just ensure config is up-to-date and save it
            self.ui.save_config()
            print("Settings backup saved via main config file")
        except Exception as e:
            print(f"Warning: Failed to save settings backup: {e}")
    
    def restore_settings_from_json(self):
        """Restore settings from JSON config file in secondary backup folder"""
        # Block if sync is in progress
        if sv.sync_in_progress:
            messagebox.showinfo(
                "Sync In Progress",
                "Please wait - background sync is in progress.\n\n"
                "Restore operations are temporarily disabled to ensure data integrity."
            )
            return
        
        backup_folder = sv.backup_folder.get().strip()
        if not backup_folder:
            messagebox.showwarning("No Backup Folder", "Please select a secondary backup folder first")
            return
        
        backup_path = Path(backup_folder)
        if not backup_path.exists():
            messagebox.showwarning("Invalid Folder", f"Secondary backup folder does not exist:\n{backup_folder}")
            return
        
        # Look for config file in JSON subfolder
        json_subfolder = backup_path / "JSON"
        settings_path = None
        
        if json_subfolder.exists():
            # Try new config file name first
            candidate = json_subfolder / ".training_log_config.json"
            if candidate.exists():
                settings_path = candidate
            else:
                # Fallback to old settings file for backward compatibility
                candidate = json_subfolder / "airscenting_settings.json"
                if candidate.exists():
                    settings_path = candidate
        
        if not settings_path:
            messagebox.showinfo("No Settings Backup", 
                               f"No settings backup file found in:\n{backup_folder}/JSON/\n\n"
                               f"Looking for: .training_log_config.json")
            return
        
        try:
            # Load settings
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            
            print(f"Restore: Loaded settings from {settings_path}")
            
            # Handle both old and new config formats
            # New format uses 'dog_names', old uses 'dogs'
            dogs = settings.get("dog_names", settings.get("dogs", []))
            locations = settings.get("training_locations", [])
            terrain_types = settings.get("terrain_types", [])
            distraction_types = settings.get("distraction_types", [])
            
            # Get handler from nested config (new) or flat (old)
            airscenting_config = settings.get("airscenting", {})
            handler_name = airscenting_config.get("default_handler", settings.get("handler_name", ""))
            
            print(f"Restore: Found dogs: {dogs}")
            print(f"Restore: Found locations: {locations}")
            
            db_type = sv.db_type.get()
            
            # Set up database connection once
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            dogs_added = 0
            locations_added = 0
            terrain_added = 0
            distraction_added = 0
            
            # Insert dogs to database
            if dogs:
                print(f"Restore: Attempting to restore {len(dogs)} dogs...")
                for dog_name in dogs:
                    try:
                        with database.get_connection() as conn:
                            # Check if dog already exists
                            check = conn.execute(
                                text("SELECT name FROM dogs WHERE name = :name"),
                                {"name": dog_name}
                            ).fetchone()
                            
                            if not check:
                                conn.execute(
                                    text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": dog_name, "user_name": get_username()}
                                )
                                conn.commit()
                                dogs_added += 1
                                print(f"Restore: Added dog '{dog_name}'")
                            else:
                                print(f"Restore: Dog '{dog_name}' already exists")
                    except Exception as e:
                        print(f"Restore: Failed to add dog '{dog_name}': {e}")
            
            # Insert locations to database
            if locations:
                print(f"Restore: Attempting to restore {len(locations)} locations...")
                for location in locations:
                    try:
                        with database.get_connection() as conn:
                            # Check if location already exists
                            check = conn.execute(
                                text("SELECT name FROM training_locations WHERE name = :name"),
                                {"name": location}
                            ).fetchone()
                            
                            if not check:
                                conn.execute(
                                    text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": location, "user_name": get_username()}
                                )
                                conn.commit()
                                locations_added += 1
                                print(f"Restore: Added location '{location}'")
                            else:
                                print(f"Restore: Location '{location}' already exists")
                    except Exception as e:
                        print(f"Restore: Failed to add location '{location}': {e}")
            
            # Insert terrain types to database
            if terrain_types:
                print(f"Restore: Attempting to restore {len(terrain_types)} terrain types...")
                for terrain in terrain_types:
                    try:
                        with database.get_connection() as conn:
                            check = conn.execute(
                                text("SELECT name FROM terrain_types WHERE name = :name"),
                                {"name": terrain}
                            ).fetchone()
                            
                            if not check:
                                conn.execute(
                                    text("INSERT INTO terrain_types (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": terrain, "user_name": get_username()}
                                )
                                conn.commit()
                                terrain_added += 1
                                print(f"Restore: Added terrain type '{terrain}'")
                    except Exception as e:
                        print(f"Restore: Failed to add terrain type '{terrain}': {e}")
            
            # Insert distraction types to database
            if distraction_types:
                print(f"Restore: Attempting to restore {len(distraction_types)} distraction types...")
                for distraction in distraction_types:
                    try:
                        with database.get_connection() as conn:
                            check = conn.execute(
                                text("SELECT name FROM distraction_types WHERE name = :name"),
                                {"name": distraction}
                            ).fetchone()
                            
                            if not check:
                                conn.execute(
                                    text("INSERT INTO distraction_types (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": distraction, "user_name": get_username()}
                                )
                                conn.commit()
                                distraction_added += 1
                                print(f"Restore: Added distraction type '{distraction}'")
                    except Exception as e:
                        print(f"Restore: Failed to add distraction type '{distraction}': {e}")
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Save handler name to nested airscenting config
            if handler_name:
                if "airscenting" not in self.ui.config:
                    self.ui.config["airscenting"] = {}
                self.ui.config["airscenting"]["default_handler"] = handler_name
                sv.default_handler.set(handler_name)
            
            self.ui.save_config()
            
            # Refresh UI
            print("Restore: Refreshing UI...")
            self.ui.load_dogs_from_database()
            if hasattr(self.ui, 'a_dog_combo'):
                self.ui.refresh_dog_list()
            
            self.ui.load_locations_from_database()
            if hasattr(self.ui, 'a_location_combo'):
                self.ui.refresh_location_list()
            
            # Reload terrain and distraction lists from database
            self.ui.load_terrain_from_database()
            self.ui.load_distraction_from_database()
            # Also refresh Entry tab terrain combobox
            if hasattr(self.ui, 'a_terrain_combo'):
                self.ui.refresh_terrain_list()
            
            print(f"Restore: Complete - {dogs_added} dogs, {locations_added} locations, {terrain_added} terrains, {distraction_added} distractions added")
            
            # Now restore sessions from JSON files in secondary backup
            sessions_restored = 0
            session_files = list(json_subfolder.glob("*session_*.json")) if json_subfolder.exists() else []
            
            if session_files:
                result = messagebox.askyesno(
                    "Restore Sessions?",
                    f"Found {len(session_files)} session backup file(s).\n\n"
                    "Do you also want to restore these sessions?",
                    icon='question'
                )
                
                if result:
                    sessions_restored = self._restore_sessions_from_backup_folder(json_subfolder, db_type)
            
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
            if handler_name:
                msg += f"Restored handler name: {handler_name}\n"
            if sessions_restored > 0:
                msg += f"Restored {sessions_restored} session(s)\n"
            
            messagebox.showinfo("Restore Complete", msg)
            
        except Exception as e:
            messagebox.showerror("Restore Error", f"Failed to restore settings:\n{e}")
            print(f"Error restoring settings: {e}")
    
    def _restore_sessions_from_backup_folder(self, json_folder, db_type):
        """
        Restore sessions from JSON backup files in a specific folder.
        
        Args:
            json_folder: Path to folder containing session JSON files
            db_type: Database type to restore to
            
        Returns:
            int: Number of sessions restored
        """
        import database
        
        json_files = list(json_folder.glob("*session_*.json"))
        if not json_files:
            return 0
        
        restored_count = 0
        
        old_db_type = None
        try:
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            from database import engine
            engine.dispose()
            from importlib import reload
            reload(database)
            
            for json_file in sorted(json_files):
                try:
                    with open(json_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Check if session already exists
                    session_num = session_data.get('session_number')
                    date_str = session_data.get('date')
                    dog_name = session_data.get('dog_name')
                    
                    # Handle image_files - convert list to JSON string if needed
                    image_files = session_data.get('image_files', session_data.get('map_files', []))
                    if isinstance(image_files, list):
                        image_files_json = json.dumps(image_files)
                    else:
                        image_files_json = image_files or ''
                    
                    with database.get_connection() as conn:
                        # Check for existing session
                        result = conn.execute(
                            text("SELECT id FROM training_sessions WHERE session_number = :num AND date = :date AND dog_name = :dog"),
                            {"num": session_num, "date": date_str, "dog": dog_name}
                        )
                        if result.fetchone():
                            continue  # Skip existing session
                        
                        # Insert session - column names must match schema.py
                        conn.execute(
                            text("""
                                INSERT INTO training_sessions (
                                    session_number, date, dog_name, location, handler,
                                    weather, temperature, wind_direction, wind_speed,
                                    session_purpose, field_support, search_area_size,
                                    num_subjects, handler_knowledge, search_type,
                                    drive_level, subjects_found, comments, image_files,
                                    user_name
                                ) VALUES (
                                    :session_number, :date, :dog_name, :location, :handler,
                                    :weather, :temperature, :wind_direction, :wind_speed,
                                    :session_purpose, :field_support, :search_area_size,
                                    :num_subjects, :handler_knowledge, :search_type,
                                    :drive_level, :subjects_found, :comments, :image_files,
                                    :user_name
                                )
                            """),
                            {
                                "session_number": session_num,
                                "date": date_str,
                                "dog_name": dog_name,
                                "location": session_data.get('location', ''),
                                "handler": session_data.get('handler_name', session_data.get('handler', '')),
                                "weather": session_data.get('weather', ''),
                                "temperature": session_data.get('temperature', ''),
                                "wind_direction": session_data.get('wind_direction', ''),
                                "wind_speed": session_data.get('wind_speed', ''),
                                "session_purpose": session_data.get('session_purpose', ''),
                                "field_support": session_data.get('field_support', ''),
                                "search_area_size": session_data.get('search_area_size', ''),
                                "num_subjects": session_data.get('num_subjects', ''),
                                "handler_knowledge": session_data.get('handler_knowledge', ''),
                                "search_type": session_data.get('search_type', ''),
                                "drive_level": session_data.get('drive_level', ''),
                                "subjects_found": session_data.get('subjects_found', ''),
                                "comments": session_data.get('notes', session_data.get('comments', '')),
                                "image_files": image_files_json,
                                "user_name": session_data.get('user_name', get_username())
                            }
                        )
                        conn.commit()
                        
                        # Get inserted session ID
                        result = conn.execute(text("SELECT last_insert_rowid()"))
                        session_id = result.fetchone()[0]
                        
                        # Restore terrain types for this session
                        terrains = session_data.get('selected_terrains', session_data.get('terrain_types', session_data.get('terrains', [])))
                        for terrain in terrains:
                            try:
                                conn.execute(
                                    text("INSERT INTO selected_terrains (session_id, terrain_name, user_name) VALUES (:sid, :name, :user)"),
                                    {"sid": session_id, "name": terrain, "user": get_username()}
                                )
                            except:
                                pass
                        
                        # Restore subject responses
                        responses = session_data.get('subject_responses', [])
                        for resp in responses:
                            try:
                                conn.execute(
                                    text("""INSERT INTO subject_responses 
                                           (session_id, subject_number, tfr, refind, user_name)
                                           VALUES (:sid, :num, :tfr, :refind, :user)"""),
                                    {"sid": session_id, "num": resp.get('subject_number', 1),
                                     "tfr": resp.get('tfr', ''), 
                                     "refind": resp.get('refind', ''),
                                     "user": get_username()}
                                )
                            except:
                                pass
                        
                        conn.commit()
                        restored_count += 1
                        
                except Exception as e:
                    print(f"Failed to restore session from {json_file}: {e}")
            
            # Restore original DB_TYPE
            if old_db_type:
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
        except Exception as e:
            print(f"Error during session restore: {e}")
            if old_db_type:
                try:
                    import config
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    from importlib import reload
                    reload(database)
                except:
                    pass
        
        return restored_count
    
    def restore_from_json_backups(self, db_type):
        """Restore database from JSON backup files in the PRIMARY storage folder"""
        from ui_utils import get_primary_json_folder
        
        # Get primary JSON folder (from sv.db_path/JSON)
        backup_path = get_primary_json_folder()
        if not backup_path:
            # Fall back to checking sv.backup_folder for backward compatibility
            backup_folder = sv.backup_folder.get().strip()
            if backup_folder:
                # Check if it's the old-style direct JSON folder or new-style with subfolder
                test_path = Path(backup_folder)
                if (test_path / "JSON").exists():
                    backup_path = test_path / "JSON"
                elif test_path.exists():
                    backup_path = test_path
            
        if not backup_path or not backup_path.exists():
            # No backup folder available, skip silently
            return False
        
        # Find all session JSON files (both old and new format)
        # Old format: session_<number>_<date>.json
        # New format: <dogname>_session_<number>_<date>.json
        json_files = list(backup_path.glob("*session_*.json"))
        if not json_files:
            # No backup files found, skip silently (this is normal for new installations)
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
            working_dialog = WorkingDialog(self.ui.root, "Restoring", 
                                         f"Restoring {len(json_files)} sessions to {db_type} database...")
            self.ui.root.update()
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
                                            "tfr": response.get('tfr'),
                                            "refind": response.get('refind'),
                                            "user_name": session_data.get('user_name', get_username())
                                        }
                                    )
                            
                            conn.commit()
                    
                    restored_count += 1
                    
                except Exception as e:
                    print(f"Failed to restore {json_file.name}: {e}")
                    failed_count += 1
            
            # Now insert all unique dog names into dogs table
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
                except Exception as e:
                    # Dog might already exist (UNIQUE constraint), that's OK
                    if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                        pass  # Duplicate is OK, continue with next dog
                    else:
                        pass  # Other errors are logged but don't stop the process
            
            # Now insert all unique location names into training_locations table
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
                except Exception as e:
                    # Location might already exist (UNIQUE constraint), that's OK
                    if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                        pass  # Duplicate is OK, continue with next location
                    else:
                        pass  # Other errors are logged but don't stop the process
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Refresh dog list in UI
            self.ui.load_dogs_from_database()
            if hasattr(self.ui, 'a_dog_combo'):
                self.ui.refresh_dog_list()
            
            # Refresh location list in UI
            self.ui.load_locations_from_database()
            if hasattr(self.ui, 'a_location_combo'):
                self.ui.refresh_location_list()
            
            # Also try to restore from config backup if it exists
            settings_restored = False
            terrain_added = 0
            distraction_added = 0
            
            # Try new config file first, then old settings file
            settings_path = backup_path / ".training_log_config.json"
            if not settings_path.exists():
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
                    self.ui.load_terrain_from_database()
                    self.ui.load_distraction_from_database()
                    # Also refresh Entry tab terrain combobox
                    if hasattr(self.ui, 'a_terrain_combo'):
                        self.ui.refresh_terrain_list()
                    
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
            working_dialog = WorkingDialog(self.ui.root, "Loading Defaults", 
                                         f"Loading default types to {db_type} database...")
            self.ui.root.update()
        else:
            working_dialog = None
        
        try:
            terrain_success, terrain_msg = db_mgr.restore_default_terrain_types()
            distraction_success, distraction_msg = db_mgr.restore_default_distraction_types()
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
        
        # Refresh UI - both Setup tab AND Entry tab
        self.ui.load_terrain_from_database()  # Setup tab treeview
        self.ui.load_distraction_from_database()  # Setup tab treeview
        
        # CRITICAL: Also refresh Entry tab comboboxes!
        if hasattr(self.ui, 'a_terrain_combo'):
            self.ui.refresh_terrain_list()  # Entry tab terrain combobox
        
        # Show summary
        if terrain_success and distraction_success:
            sv.status.set(f"{terrain_msg}; {distraction_msg}")
            # Auto-backup settings after loading defaults
            self.save_settings_backup()
        else:
            errors = []
            if not terrain_success:
                errors.append(f"Terrain: {terrain_msg}")
            if not distraction_success:
                errors.append(f"Distraction: {distraction_msg}")
            messagebox.showerror("Error", "\n".join(errors))
    
    def ensure_db_ready(self):
        """Ensure database connection is ready (password set for networked DBs)"""
        db_type = sv.db_type.get()
        if db_type in ["postgres", "supabase", "mysql"]:
            # Check if password field exists yet (it's created in setup_setup_tab)
            if not hasattr(self.ui, 'db_password_var'):
                return  # Too early in initialization
            
            password = sv.db_password.get().strip()
            
            # If password not loaded yet, try loading from encrypted storage
            if not password and hasattr(self.ui, 'config'):
                from password_manager import get_decrypted_password, check_crypto_available
                if check_crypto_available():
                    saved_password = get_decrypted_password(self.ui.config, db_type)
                    if saved_password:
                        sv.db_password.set(saved_password)
                        password = saved_password
            
            # Set password in database config
            if password:
                self.ui.set_db_password()
