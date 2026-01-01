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
    
    def load_initial_database_data(self):
        """Load all initial database data after splash screen starts"""
        # Use chained after() calls to let event loop run between operations
        # This keeps splash countdown and progress bars animating
        
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
                    next_session = DatabaseOperations(self.ui).get_next_session_number(last_dog)
                    sv.session_number.set(str(next_session))
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
        
        # Start the chain
        step1()
    
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
        """Save session data to JSON backup file"""
        backup_folder = sv.backup_folder.get().strip()
        if not backup_folder:
            # No backup folder configured, skip
            return
        
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
        backup_folder = sv.backup_folder.get().strip()
        if not backup_folder:
            # No backup folder configured, skip
            return
        
        backup_path = Path(backup_folder)
        if not backup_path.exists():
            print(f"Warning: Backup folder does not exist: {backup_folder}")
            return
        
        try:
            db_type = sv.db_type.get()
            
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
            handler_name = self.ui.config.get("handler_name", "")
            
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
        backup_folder = sv.backup_folder.get().strip()
        if not backup_folder:
            messagebox.showwarning("No Backup Folder", "Please select a backup folder first")
            return
        
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
            
            db_type = sv.db_type.get()
            
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
                self.ui.config["handler_name"] = settings["handler_name"]
                sv.default_handler.set(settings["handler_name"])
            
            self.ui.save_config()
            
            # Refresh UI
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
        backup_folder = sv.backup_folder.get().strip()
        if not backup_folder:
            messagebox.showwarning("No Backup Folder", "No backup folder configured")
            return False
        
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
            messagebox.showinfo("Success", 
                f"{terrain_msg}\n{distraction_msg}")
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
