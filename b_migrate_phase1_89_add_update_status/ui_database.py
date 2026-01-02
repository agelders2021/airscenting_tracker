"""
Database Operations for Air-Scenting Logger
Handles all database interactions - separated from UI logic
"""
import json
import os
from sqlalchemy import text
from datetime import datetime
import config
from database import engine, get_connection
from ui_utils import get_username, get_default_terrain_types, get_default_distraction_types


class DatabaseManager:
    """Manages all database operations for the application"""
    
    def __init__(self, db_type="sqlite"):
        """Initialize database manager"""
        self.db_type = db_type
    
    def _db_exists(self):
        """Check if database exists"""
        if self.db_type == "sqlite":
            db_path = config.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            return os.path.exists(db_path)
        # For postgres/supabase, assume exists if we can connect
        return True
    
    def _switch_db_context(self):
        """Switch to the configured database type and return old type"""
        old_db_type = config.DB_TYPE
        config.DB_TYPE = self.db_type
        
        # Reload database module
        engine.dispose()
        from importlib import reload
        import database
        reload(database)
        
        return old_db_type
    
    def _restore_db_context(self, old_db_type):
        """Restore the original database type"""
        config.DB_TYPE = old_db_type
        engine.dispose()
        from importlib import reload
        import database
        reload(database)
    
    # ===== SETTINGS =====
    
    def save_setting(self, key, value):
        """Save a setting to the database settings table"""
        if not self._db_exists():
            return
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Try to update first
                result = conn.execute(
                    text("UPDATE settings SET value = :value, updated_at = CURRENT_TIMESTAMP WHERE key = :key"),
                    {"key": key, "value": value}
                )
                
                # If no rows updated, insert new
                if result.rowcount == 0:
                    conn.execute(
                        text("INSERT INTO settings (key, value) VALUES (:key, :value)"),
                        {"key": key, "value": value}
                    )
                
                conn.commit()
            
            self._restore_db_context(old_db_type)
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" not in str(e).lower() and "does not exist" not in str(e).lower():
                print(f"Error saving database setting '{key}': {e}")
    
    def load_setting(self, key, default=None):
        """Load a setting from the database settings table"""
        if not self._db_exists():
            return default
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("SELECT value FROM settings WHERE key = :key"),
                    {"key": key}
                )
                row = result.fetchone()
            
            self._restore_db_context(old_db_type)
            
            return row[0] if row else default
                
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return default
            else:
                print(f"Error loading database setting '{key}': {e}")
                return default
    
    # ===== SESSIONS =====
    
    def get_next_session_number(self, dog_name):
        """Get the next session number for the specified dog (MAX + 1)"""
        if not dog_name or not dog_name.strip():
            return 1
        
        dog_name = dog_name.strip()
        
        if not self._db_exists():
            return 1
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                max_result = conn.execute(
                    text("SELECT MAX(session_number) FROM training_sessions WHERE dog_name = :dog_name"),
                    {"dog_name": dog_name}
                )
                max_num = max_result.scalar()
            
            self._restore_db_context(old_db_type)
            
            return (max_num or 0) + 1
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return 1
            else:
                print(f"Error getting next session number: {e}")
                return 1
    
    def save_session(self, session_data):
        """
        Save or update a training session
        
        Args:
            session_data: dict with session fields
            
        Returns:
            (success: bool, message: str, session_id: int or None)
        """
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Check if session exists
                result = conn.execute(
                    text("SELECT id FROM training_sessions WHERE session_number = :session_number AND dog_name = :dog_name"),
                    {"session_number": session_data["session_number"], "dog_name": session_data["dog_name"]}
                )
                existing = result.fetchone()
                
                if existing:
                    # Update existing session
                    conn.execute(
                        text("""
                            UPDATE training_sessions 
                            SET date = :date,
                                handler = :handler,
                                session_purpose = :session_purpose,
                                field_support = :field_support,
                                dog_name = :dog_name,
                                location = :location,
                                search_area_size = :search_area_size,
                                num_subjects = :num_subjects,
                                handler_knowledge = :handler_knowledge,
                                weather = :weather,
                                temperature = :temperature,
                                wind_direction = :wind_direction,
                                wind_speed = :wind_speed,
                                search_type = :search_type,
                                drive_level = :drive_level,
                                subjects_found = :subjects_found,
                                comments = :comments,
                                image_files = :image_files,
                                status = 'active',
                                user_name = :user_name,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE session_number = :session_number AND dog_name = :old_dog_name
                        """),
                        {
                            **session_data,
                            "old_dog_name": session_data["dog_name"],
                            "user_name": get_username()
                        }
                    )
                    conn.commit()
                    session_id = existing[0]
                    message = f"Session #{session_data['session_number']} updated successfully!"
                else:
                    # Insert new session
                    conn.execute(
                        text("""
                            INSERT INTO training_sessions 
                            (date, session_number, handler, session_purpose, field_support, dog_name, location,
                             search_area_size, num_subjects, handler_knowledge, weather, temperature, 
                             wind_direction, wind_speed, search_type, drive_level, subjects_found, comments, image_files, status, user_name)
                            VALUES (:date, :session_number, :handler, :session_purpose, :field_support, :dog_name, :location,
                                    :search_area_size, :num_subjects, :handler_knowledge, :weather, :temperature, 
                                    :wind_direction, :wind_speed, :search_type, :drive_level, :subjects_found, :comments, :image_files, 'active', :user_name)
                        """),
                        {**session_data, "user_name": get_username()}
                    )
                    conn.commit()
                    
                    # Get the new session_id
                    result = conn.execute(
                        text("SELECT id FROM training_sessions WHERE session_number = :session_number AND dog_name = :dog_name"),
                        {"session_number": session_data["session_number"], "dog_name": session_data["dog_name"]}
                    )
                    session_id = result.scalar()
                    message = f"Session #{session_data['session_number']} saved successfully!"
            
            self._restore_db_context(old_db_type)
            
            return True, message, session_id
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error saving session: {e}")
            return False, f"Database error: {e}", None
    
    def load_session(self, session_number, dog_name):
        """
        Load session data from database
        
        Returns:
            dict with session data or None if not found
        """
        if not dog_name or not dog_name.strip():
            return None
        
        dog_name = dog_name.strip()
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, date, handler, session_purpose, field_support, dog_name, location,
                               search_area_size, num_subjects, handler_knowledge, weather, temperature,
                               wind_direction, wind_speed, search_type, drive_level, subjects_found, comments, image_files
                        FROM training_sessions 
                        WHERE session_number = :session_number AND dog_name = :dog_name
                    """),
                    {"session_number": session_number, "dog_name": dog_name}
                )
                row = result.fetchone()
            
            self._restore_db_context(old_db_type)
            
            if row:
                return {
                    "id": row[0],
                    "date": str(row[1]),
                    "handler": row[2] or "",
                    "session_purpose": row[3] or "",
                    "field_support": row[4] or "",
                    "dog_name": row[5] or "",
                    "location": row[6] or "",
                    "search_area_size": row[7] or "",
                    "num_subjects": row[8] or "",
                    "handler_knowledge": row[9] or "",
                    "weather": row[10] or "",
                    "temperature": row[11] or "",
                    "wind_direction": row[12] or "",
                    "wind_speed": row[13] or "",
                    "search_type": row[14] or "",
                    "drive_level": row[15] or "",
                    "subjects_found": row[16] or "",
                    "comments": row[17] or "",
                    "image_files": row[18] or ""
                }
            
            return None
                
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error loading session: {e}")
            return None
    
    def delete_sessions(self, session_numbers, dog_name):
        """Delete multiple sessions for a specific dog"""
        if not dog_name or not dog_name.strip():
            return False, "No dog specified"
        
        dog_name = dog_name.strip()
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                for session_num in session_numbers:
                    conn.execute(
                        text("DELETE FROM training_sessions WHERE session_number = :session_number AND dog_name = :dog_name"),
                        {"session_number": session_num, "dog_name": dog_name}
                    )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            
            return True, f"Deleted {len(session_numbers)} session(s)"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error deleting sessions: {e}")
            return False, f"Database error: {e}"
    
    def update_session_status(self, session_number, dog_name, new_status):
        """Update the status of a session (for delete/undelete)
        
        Args:
            session_number: Session number to update
            dog_name: Dog name
            new_status: 'active' or 'deleted'
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not dog_name or not dog_name.strip():
            return False
        
        dog_name = dog_name.strip()
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                conn.execute(
                    text("""
                        UPDATE training_sessions 
                        SET status = :status, updated_at = CURRENT_TIMESTAMP
                        WHERE session_number = :session_number AND dog_name = :dog_name
                    """),
                    {"status": new_status, "session_number": session_number, "dog_name": dog_name}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            
            return True
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error updating session status: {e}")
            return False
    
    def get_sessions_for_dog(self, dog_name, status_filter='active'):
        """Get sessions for a specific dog filtered by status
        
        Args:
            dog_name: Name of the dog
            status_filter: 'active', 'deleted', or 'both'
        
        Returns:
            List of tuples: (session_number, date, handler, dog_name)
        """
        if not dog_name or not dog_name.strip():
            return []
        
        dog_name = dog_name.strip()
        
        try:
            old_db_type = self._switch_db_context()
            
            # Build WHERE clause based on status filter
            if status_filter == 'active':
                status_where = "AND (status = 'active' OR status IS NULL)"
            elif status_filter == 'deleted':
                status_where = "AND status = 'deleted'"
            else:  # 'both'
                status_where = ""
            
            with get_connection() as conn:
                result = conn.execute(
                    text(f"""
                        SELECT session_number, date, handler, dog_name
                        FROM training_sessions 
                        WHERE dog_name = :dog_name {status_where}
                        ORDER BY date, session_number
                    """),
                    {"dog_name": dog_name}
                )
                sessions = result.fetchall()
            
            self._restore_db_context(old_db_type)
            
            return sessions
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return []
            else:
                print(f"Error getting sessions: {e}")
                return []
    
    def compute_session_number(self, dog_name, session_date, status_filter='active'):
        """Compute the ordinal session number for a session based on filtered list
        
        Args:
            dog_name: Name of the dog
            session_date: Date of the session (as string 'YYYY-MM-DD')
            status_filter: 'active', 'deleted', or 'both'
        
        Returns:
            int: Ordinal position (1-based) in the filtered list
        """
        if not dog_name or not dog_name.strip():
            return 1
        
        dog_name = dog_name.strip()
        
        try:
            old_db_type = self._switch_db_context()
            
            # Build WHERE clause based on status filter
            if status_filter == 'active':
                status_where = "AND (status = 'active' OR status IS NULL)"
            elif status_filter == 'deleted':
                status_where = "AND status = 'deleted'"
            else:  # 'both'
                status_where = ""
            
            with get_connection() as conn:
                # Count sessions with same dog, matching status, with date <= given date
                result = conn.execute(
                    text(f"""
                        SELECT COUNT(*) 
                        FROM training_sessions 
                        WHERE dog_name = :dog_name 
                        AND date <= :session_date
                        {status_where}
                    """),
                    {"dog_name": dog_name, "session_date": session_date}
                )
                count = result.scalar()
            
            self._restore_db_context(old_db_type)
            
            # Return count as ordinal position (minimum 1)
            return count if count > 0 else 1
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return 1
            else:
                print(f"Error computing session number: {e}")
                return 1
    
    # ===== SELECTED TERRAINS =====
    
    def save_selected_terrains(self, session_id, terrain_list):
        """Save selected terrains for a session"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Delete existing
                conn.execute(
                    text("DELETE FROM selected_terrains WHERE session_id = :session_id"),
                    {"session_id": session_id}
                )
                
                # Insert new
                for terrain_name in terrain_list:
                    conn.execute(
                        text("""
                            INSERT INTO selected_terrains (session_id, terrain_name, user_name)
                            VALUES (:session_id, :terrain_name, :user_name)
                        """),
                        {
                            "session_id": session_id,
                            "terrain_name": terrain_name,
                            "user_name": get_username()
                        }
                    )
                
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error saving selected terrains: {e}")
            return False
    
    def load_selected_terrains(self, session_id):
        """Load selected terrains for a session"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("SELECT terrain_name FROM selected_terrains WHERE session_id = :session_id ORDER BY terrain_name"),
                    {"session_id": session_id}
                )
                terrains = [row[0] for row in result]
            
            self._restore_db_context(old_db_type)
            return terrains
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error loading selected terrains: {e}")
            return []
    
    # ===== SUBJECT RESPONSES =====
    
    def save_subject_responses(self, session_id, responses_list):
        """Save subject responses for a session"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Delete existing
                conn.execute(
                    text("DELETE FROM subject_responses WHERE session_id = :session_id"),
                    {"session_id": session_id}
                )
                
                # Insert new
                for response in responses_list:
                    if response.get("tfr") or response.get("refind"):
                        conn.execute(
                            text("""
                                INSERT INTO subject_responses (session_id, subject_number, tfr, refind, user_name)
                                VALUES (:session_id, :subject_number, :tfr, :refind, :user_name)
                            """),
                            {
                                "session_id": session_id,
                                "subject_number": response["subject_number"],
                                "tfr": response.get("tfr", ""),
                                "refind": response.get("refind", ""),
                                "user_name": get_username()
                            }
                        )
                
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error saving subject responses: {e}")
            return False
    
    def load_subject_responses(self, session_id):
        """Load subject responses for a session"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("""
                        SELECT subject_number, tfr, refind 
                        FROM subject_responses 
                        WHERE session_id = :session_id 
                        ORDER BY subject_number
                    """),
                    {"session_id": session_id}
                )
                responses = [
                    {
                        "subject_number": row[0],
                        "tfr": row[1] or "",
                        "refind": row[2] or ""
                    }
                    for row in result
                ]
            
            self._restore_db_context(old_db_type)
            return responses
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error loading subject responses: {e}")
            return []
    
    # ===== DOGS =====
    
    def load_dogs(self):
        """Load all dog names from database"""
        if not self._db_exists():
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(text("SELECT name FROM dogs ORDER BY name"))
                dogs = [row[0] for row in result]
            
            self._restore_db_context(old_db_type)
            return dogs
                
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return []
            else:
                print(f"Error loading dogs: {e}")
                return []
    
    def add_dog(self, dog_name):
        """Add a new dog to the database"""
        dog_name = dog_name.strip()
        if not dog_name:
            return False, "Dog name cannot be empty"
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                conn.execute(
                    text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                    {"name": dog_name, "user_name": get_username()}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Added dog: {dog_name}"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return False, f"Dog '{dog_name}' already exists"
            else:
                print(f"Error adding dog: {e}")
                return False, f"Database error: {e}"
    
    def remove_dog(self, dog_name):
        """Remove a dog from the database"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                conn.execute(
                    text("DELETE FROM dogs WHERE name = :name"),
                    {"name": dog_name}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Removed dog: {dog_name}"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error removing dog: {e}")
            return False, f"Database error: {e}"
    
    # ===== LOCATIONS =====
    
    def load_locations(self):
        """Load all training locations from database"""
        if not self._db_exists():
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(text("SELECT name FROM training_locations ORDER BY name"))
                locations = [row[0] for row in result]
            
            self._restore_db_context(old_db_type)
            return locations
                
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return []
            else:
                print(f"Error loading locations: {e}")
                return []
    
    def add_location(self, location):
        """Add a new training location"""
        location = location.strip()
        if not location:
            return False, "Location cannot be empty"
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                conn.execute(
                    text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                    {"name": location, "user_name": get_username()}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Added location: {location}"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return False, f"Location '{location}' already exists"
            else:
                print(f"Error adding location: {e}")
                return False, f"Database error: {e}"
    
    def remove_location(self, location):
        """Remove a training location"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                conn.execute(
                    text("DELETE FROM training_locations WHERE name = :name"),
                    {"name": location}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Removed location: {location}"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error removing location: {e}")
            return False, f"Database error: {e}"
    
    # ===== TERRAIN TYPES =====
    
    def load_terrain_types(self):
        """Load all terrain types from database ordered by sort_order"""
        if not self._db_exists():
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(text("SELECT name FROM terrain_types ORDER BY sort_order, name"))
                terrain_types = [row[0] for row in result]
            
            self._restore_db_context(old_db_type)
            return terrain_types
                
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return []
            else:
                print(f"Error loading terrain types: {e}")
                return []
    
    def add_terrain_type(self, terrain):
        """Add a new terrain type with next available sort_order"""
        terrain = terrain.strip()
        if not terrain:
            return False, "Terrain type cannot be empty"
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Get next sort_order (max + 1)
                result = conn.execute(text("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM terrain_types"))
                next_order = result.scalar()
                
                conn.execute(
                    text("INSERT INTO terrain_types (name, user_name, sort_order) VALUES (:name, :user_name, :sort_order)"),
                    {"name": terrain, "user_name": get_username(), "sort_order": next_order}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Added terrain type: {terrain}"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return False, f"Terrain type '{terrain}' already exists"
            else:
                print(f"Error adding terrain type: {e}")
                return False, f"Database error: {e}"
    
    def remove_terrain_type(self, terrain):
        """Remove a terrain type"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                conn.execute(
                    text("DELETE FROM terrain_types WHERE name = :name"),
                    {"name": terrain}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Removed terrain type: {terrain}"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error removing terrain type: {e}")
            return False, f"Database error: {e}"
    
    def move_terrain_up(self, terrain):
        """Move terrain type up in sort order"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Get current item's sort_order
                result = conn.execute(
                    text("SELECT sort_order FROM terrain_types WHERE name = :name"),
                    {"name": terrain}
                )
                row = result.fetchone()
                if not row:
                    self._restore_db_context(old_db_type)
                    return False, f"Terrain type '{terrain}' not found"
                
                current_order = row[0]
                
                # Find item above (lower sort_order)
                result = conn.execute(
                    text("SELECT name, sort_order FROM terrain_types WHERE sort_order < :order ORDER BY sort_order DESC LIMIT 1"),
                    {"order": current_order}
                )
                prev_row = result.fetchone()
                
                if not prev_row:
                    self._restore_db_context(old_db_type)
                    return False, "Already at top"
                
                prev_name, prev_order = prev_row
                
                # Swap sort_order values
                conn.execute(
                    text("UPDATE terrain_types SET sort_order = :new_order WHERE name = :name"),
                    {"new_order": prev_order, "name": terrain}
                )
                conn.execute(
                    text("UPDATE terrain_types SET sort_order = :new_order WHERE name = :name"),
                    {"new_order": current_order, "name": prev_name}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Moved '{terrain}' up"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error moving terrain type up: {e}")
            return False, f"Database error: {e}"
    
    def move_terrain_down(self, terrain):
        """Move terrain type down in sort order"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Get current item's sort_order
                result = conn.execute(
                    text("SELECT sort_order FROM terrain_types WHERE name = :name"),
                    {"name": terrain}
                )
                row = result.fetchone()
                if not row:
                    self._restore_db_context(old_db_type)
                    return False, f"Terrain type '{terrain}' not found"
                
                current_order = row[0]
                
                # Find item below (higher sort_order)
                result = conn.execute(
                    text("SELECT name, sort_order FROM terrain_types WHERE sort_order > :order ORDER BY sort_order ASC LIMIT 1"),
                    {"order": current_order}
                )
                next_row = result.fetchone()
                
                if not next_row:
                    self._restore_db_context(old_db_type)
                    return False, "Already at bottom"
                
                next_name, next_order = next_row
                
                # Swap sort_order values
                conn.execute(
                    text("UPDATE terrain_types SET sort_order = :new_order WHERE name = :name"),
                    {"new_order": next_order, "name": terrain}
                )
                conn.execute(
                    text("UPDATE terrain_types SET sort_order = :new_order WHERE name = :name"),
                    {"new_order": current_order, "name": next_name}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Moved '{terrain}' down"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error moving terrain type down: {e}")
            return False, f"Database error: {e}"
    
    def restore_default_terrain_types(self):
        """Replace all terrain types with defaults"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Delete all existing
                conn.execute(text("DELETE FROM terrain_types"))
                
                # Insert defaults with proper sort_order
                defaults = get_default_terrain_types()
                for idx, terrain in enumerate(defaults):
                    conn.execute(
                        text("INSERT INTO terrain_types (name, user_name, sort_order) VALUES (:name, :user_name, :sort_order)"),
                        {"name": terrain, "user_name": get_username(), "sort_order": idx}
                    )
                
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Restored {len(defaults)} default terrain types"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error restoring default terrain types: {e}")
            return False, f"Database error: {e}"
    
    # ===== DISTRACTION TYPES =====
    
    def load_distraction_types(self):
        """Load all distraction types from database ordered by sort_order"""
        if not self._db_exists():
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(text("SELECT name FROM distraction_types ORDER BY sort_order, name"))
                distraction_types = [row[0] for row in result]
            
            self._restore_db_context(old_db_type)
            return distraction_types
                
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" in str(e).lower() or "does not exist" in str(e).lower():
                return []
            else:
                print(f"Error loading distraction types: {e}")
                return []
    
    def add_distraction_type(self, distraction):
        """Add a new distraction type with next available sort_order"""
        distraction = distraction.strip()
        if not distraction:
            return False, "Distraction type cannot be empty"
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Get next sort_order (max + 1)
                result = conn.execute(text("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM distraction_types"))
                next_order = result.scalar()
                
                conn.execute(
                    text("INSERT INTO distraction_types (name, user_name, sort_order) VALUES (:name, :user_name, :sort_order)"),
                    {"name": distraction, "user_name": get_username(), "sort_order": next_order}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Added distraction type: {distraction}"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return False, f"Distraction type '{distraction}' already exists"
            else:
                print(f"Error adding distraction type: {e}")
                return False, f"Database error: {e}"
    
    def remove_distraction_type(self, distraction):
        """Remove a distraction type"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                conn.execute(
                    text("DELETE FROM distraction_types WHERE name = :name"),
                    {"name": distraction}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Removed distraction type: {distraction}"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error removing distraction type: {e}")
            return False, f"Database error: {e}"
    
    def move_distraction_up(self, distraction):
        """Move distraction type up in sort order"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Get current item's sort_order
                result = conn.execute(
                    text("SELECT sort_order FROM distraction_types WHERE name = :name"),
                    {"name": distraction}
                )
                row = result.fetchone()
                if not row:
                    self._restore_db_context(old_db_type)
                    return False, f"Distraction type '{distraction}' not found"
                
                current_order = row[0]
                
                # Find item above (lower sort_order)
                result = conn.execute(
                    text("SELECT name, sort_order FROM distraction_types WHERE sort_order < :order ORDER BY sort_order DESC LIMIT 1"),
                    {"order": current_order}
                )
                prev_row = result.fetchone()
                
                if not prev_row:
                    self._restore_db_context(old_db_type)
                    return False, "Already at top"
                
                prev_name, prev_order = prev_row
                
                # Swap sort_order values
                conn.execute(
                    text("UPDATE distraction_types SET sort_order = :new_order WHERE name = :name"),
                    {"new_order": prev_order, "name": distraction}
                )
                conn.execute(
                    text("UPDATE distraction_types SET sort_order = :new_order WHERE name = :name"),
                    {"new_order": current_order, "name": prev_name}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Moved '{distraction}' up"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error moving distraction type up: {e}")
            return False, f"Database error: {e}"
    
    def move_distraction_down(self, distraction):
        """Move distraction type down in sort order"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Get current item's sort_order
                result = conn.execute(
                    text("SELECT sort_order FROM distraction_types WHERE name = :name"),
                    {"name": distraction}
                )
                row = result.fetchone()
                if not row:
                    self._restore_db_context(old_db_type)
                    return False, f"Distraction type '{distraction}' not found"
                
                current_order = row[0]
                
                # Find item below (higher sort_order)
                result = conn.execute(
                    text("SELECT name, sort_order FROM distraction_types WHERE sort_order > :order ORDER BY sort_order ASC LIMIT 1"),
                    {"order": current_order}
                )
                next_row = result.fetchone()
                
                if not next_row:
                    self._restore_db_context(old_db_type)
                    return False, "Already at bottom"
                
                next_name, next_order = next_row
                
                # Swap sort_order values
                conn.execute(
                    text("UPDATE distraction_types SET sort_order = :new_order WHERE name = :name"),
                    {"new_order": next_order, "name": distraction}
                )
                conn.execute(
                    text("UPDATE distraction_types SET sort_order = :new_order WHERE name = :name"),
                    {"new_order": current_order, "name": next_name}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Moved '{distraction}' down"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error moving distraction type down: {e}")
            return False, f"Database error: {e}"
    
    def restore_default_distraction_types(self):
        """Replace all distraction types with defaults"""
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Delete all existing
                conn.execute(text("DELETE FROM distraction_types"))
                
                # Insert defaults with proper sort_order
                defaults = get_default_distraction_types()
                for idx, distraction in enumerate(defaults):
                    conn.execute(
                        text("INSERT INTO distraction_types (name, user_name, sort_order) VALUES (:name, :user_name, :sort_order)"),
                        {"name": distraction, "user_name": get_username(), "sort_order": idx}
                    )
                
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True, f"Restored {len(defaults)} default distraction types"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error restoring default distraction types: {e}")
            return False, f"Database error: {e}"



# Module-level convenience functions
_default_db_manager = None

def get_db_manager(db_type="sqlite"):
    """Get or create the default database manager"""
    global _default_db_manager
    if _default_db_manager is None or _default_db_manager.db_type != db_type:
        _default_db_manager = DatabaseManager(db_type)
    return _default_db_manager


# ===== DATABASE OPERATIONS WRAPPER =====
# Provides UI-compatible interface to DatabaseManager

class DatabaseOperations:
    """
    Wrapper class to provide UI-compatible interface to DatabaseManager.
    This allows UI code to use: DatabaseOperations(ui).method()
    while internally delegating to DatabaseManager.
    """
    
    def __init__(self, ui):
        """Initialize with UI reference to access sv variables"""
        self.ui = ui
        import sv as sv_module
        db_type = sv_module.sv.db_type.get()
        self.db_manager = get_db_manager(db_type)
    
    def get_next_session_number(self, dog_name=None):
        """Get next session number for dog"""
        if dog_name is None:
            import sv as sv_module
            dog_name = sv_module.sv.dog.get()
        return self.db_manager.get_next_session_number(dog_name)
    
    def save_db_setting(self, key, value):
        """Save a setting to database"""
        return self.db_manager.save_setting(key, value)
    
    def load_db_setting(self, key, default=None):
        """Load a setting from database"""
        return self.db_manager.load_setting(key, default)
    
    def get_session_data(self, session_number, dog_name):
        """
        Get session data as tuple (for backward compatibility with UI code).
        
        Returns tuple in this order:
        (date, handler, session_purpose, field_support, dog_name, location,
         search_area_size, num_subjects, handler_knowledge, weather, temperature,
         wind_direction, wind_speed, search_type, drive_level, subjects_found,
         image_files, comments)
         
        NOTE: comments is at index 17 (row[17])
        
        Or None if session not found.
        """
        session_dict = self.db_manager.load_session(session_number, dog_name)
        
        if session_dict is None:
            return None
        
        # Convert dict to tuple in the order expected by UI code
        return (
            session_dict["date"],           # row[0]
            session_dict["handler"],        # row[1]
            session_dict["session_purpose"], # row[2]
            session_dict["field_support"],  # row[3]
            session_dict["dog_name"],       # row[4]
            session_dict["location"],       # row[5]
            session_dict["search_area_size"], # row[6]
            session_dict["num_subjects"],   # row[7]
            session_dict["handler_knowledge"], # row[8]
            session_dict["weather"],        # row[9]
            session_dict["temperature"],    # row[10]
            session_dict["wind_direction"], # row[11]
            session_dict["wind_speed"],     # row[12]
            session_dict["search_type"],    # row[13]
            session_dict["drive_level"],    # row[14]
            session_dict["subjects_found"], # row[15]
            session_dict["image_files"],    # row[16]
            session_dict["comments"]        # row[17] ← ADDED!
        )
    
    def get_session_with_related_data(self, session_number, dog_name):
        """
        Get complete session data including related data (terrains, responses).
        Returns a dict with all session info.
        """
        session_dict = self.db_manager.load_session(session_number, dog_name)
        
        if session_dict is None:
            return None
        
        # Get session ID for loading related data
        session_id = session_dict.get("id")
        
        if session_id:
            # Load selected terrains
            selected_terrains = self.db_manager.load_selected_terrains(session_id)
            session_dict["selected_terrains"] = selected_terrains
            
            # Load subject responses
            subject_responses = self.db_manager.load_subject_responses(session_id)
            session_dict["subject_responses"] = subject_responses
        else:
            session_dict["selected_terrains"] = []
            session_dict["subject_responses"] = []
        
        return session_dict
    
    def get_all_sessions_for_dog(self, dog_name, status_filter='active'):
        """Get all sessions for a dog filtered by status (returns list of tuples)"""
        return self.db_manager.get_sessions_for_dog(dog_name, status_filter)
    
    def delete_sessions(self, session_numbers, dog_name):
        """Delete multiple sessions"""
        return self.db_manager.delete_sessions(session_numbers, dog_name)

    def dispose_all_engines(self):
        """
        Dispose all database engine connections
        
        Forces all engines to close connections and reconnect on next use.
        Useful when database password changes.
        """
        try:
            # Import here to avoid circular imports
            from database import engine
            import config
            from importlib import reload
            import database as db_module
            
            # Dispose the main engine
            engine.dispose()
            
            # Reload database module to pick up new configuration
            reload(db_module)
            
            print("[OK] All database engines disposed and reloaded")
            
        except Exception as e:
            print(f"[WARN] Error disposing engines: {e}")



