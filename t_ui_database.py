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
Database Operations for Trailing Logger
Handles all database interactions for trailing sessions - separated from UI logic
"""
import json
import os
from sqlalchemy import text
from datetime import datetime
import t_config as config
from database import engine, get_connection
from ui_utils import get_username, get_default_terrain_types, get_default_distraction_types
from backup_management import generate_session_uuid, get_current_update_time


class DatabaseManager:
    """Manages all database operations for the trailing application"""
    
    def __init__(self, db_type="sqlite"):
        """Initialize database manager"""
        self.db_type = db_type
    
    def _db_exists(self):
        """Check if database exists"""
        if self.db_type == "sqlite":
            db_path = config.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            return os.path.exists(db_path)
        return True
    
    def _switch_db_context(self):
        """Switch to the configured database type and return old type"""
        old_db_type = config.DB_TYPE
        config.DB_TYPE = self.db_type
        
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
                result = conn.execute(
                    text("UPDATE settings SET value = :value, updated_at = CURRENT_TIMESTAMP WHERE key = :key"),
                    {"key": key, "value": value}
                )
                
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
            
            if row:
                return row[0]
            return default
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            if "no such table" not in str(e).lower() and "does not exist" not in str(e).lower():
                print(f"Error loading database setting '{key}': {e}")
            return default
    
    # ===== TRAILING SESSION OPERATIONS =====
    
    def get_next_session_number(self, dog_name=None):
        """Get the next session number for a dog"""
        if not self._db_exists() or not dog_name:
            return 1
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("SELECT MAX(t_session_number) FROM t_training_sessions WHERE t_dog_name = :dog_name"),
                    {"dog_name": dog_name}
                )
                row = result.fetchone()
            
            self._restore_db_context(old_db_type)
            
            if row and row[0]:
                return row[0] + 1
            return 1
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error getting next session number: {e}")
            return 1
    
    def save_trailing_session(self, session_data, is_update=False):
        """
        Save or update a trailing session to the database
        
        Args:
            session_data: Dictionary with all session fields (t_ prefixed)
            is_update: If True, update existing; if False, insert new
            
        Returns:
            tuple: (success: bool, session_id: int or None, message: str)
        """
        if not self._db_exists():
            return False, None, "Database not configured"
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                session_number = session_data.get('t_session_number')
                dog_name = session_data.get('t_dog_name')
                
                if is_update:
                    # Check if session exists
                    result = conn.execute(
                        text("SELECT id, uuid FROM t_training_sessions WHERE t_session_number = :session_number AND t_dog_name = :dog_name"),
                        {"session_number": session_number, "dog_name": dog_name}
                    )
                    existing = result.fetchone()
                    
                    if existing:
                        session_id = existing[0]
                        existing_uuid = existing[1]
                        
                        # Keep existing UUID, update timestamp
                        conn.execute(
                            text("""
                                UPDATE t_training_sessions SET
                                    t_date = :t_date,
                                    t_handler = :t_handler,
                                    t_field_support = :t_field_support,
                                    t_location = :t_location,
                                    t_start_time = :t_start_time,
                                    t_finish_time = :t_finish_time,
                                    t_trail_age = :t_trail_age,
                                    t_trail_length = :t_trail_length,
                                    t_difficulty = :t_difficulty,
                                    t_trail_layer = :t_trail_layer,
                                    t_cross_track_layer = :t_cross_track_layer,
                                    t_cross_track_age = :t_cross_track_age,
                                    t_weather_laying = :t_weather_laying,
                                    t_temperature_laying = :t_temperature_laying,
                                    t_wind_speed_laying = :t_wind_speed_laying,
                                    t_wind_direction_laying = :t_wind_direction_laying,
                                    t_humidity_laying = :t_humidity_laying,
                                    t_weather_running = :t_weather_running,
                                    t_temperature_running = :t_temperature_running,
                                    t_wind_speed_running = :t_wind_speed_running,
                                    t_wind_direction_running = :t_wind_direction_running,
                                    t_humidity_running = :t_humidity_running,
                                    t_start_behavior = :t_start_behavior,
                                    t_consistency = :t_consistency,
                                    t_head_position = :t_head_position,
                                    t_pace = :t_pace,
                                    t_indication = :t_indication,
                                    t_time_to_complete = :t_time_to_complete,
                                    t_success_rate = :t_success_rate,
                                    t_impression = :t_impression,
                                    t_map_files = :t_map_files,
                                    update_time = :update_time,
                                    user_name = :user_name
                                WHERE t_session_number = :t_session_number AND t_dog_name = :t_dog_name
                            """),
                            {
                                **session_data,
                                "update_time": get_current_update_time(),
                                "user_name": get_username()
                            }
                        )
                        conn.commit()
                        self._restore_db_context(old_db_type)
                        return True, session_id, "Session updated successfully"
                    else:
                        # Session doesn't exist for update, insert instead
                        is_update = False
                
                if not is_update:
                    # Generate new UUID for new session
                    new_uuid = generate_session_uuid()
                    
                    conn.execute(
                        text("""
                            INSERT INTO t_training_sessions (
                                t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                                t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                                t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                                t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                                t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                                t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                                t_time_to_complete, t_success_rate, t_impression, t_map_files,
                                uuid, update_time, user_name, status
                            ) VALUES (
                                :t_session_number, :t_dog_name, :t_date, :t_handler, :t_field_support,
                                :t_location, :t_start_time, :t_finish_time, :t_trail_age, :t_trail_length,
                                :t_difficulty, :t_trail_layer, :t_cross_track_layer, :t_cross_track_age,
                                :t_weather_laying, :t_temperature_laying, :t_wind_speed_laying, :t_wind_direction_laying, :t_humidity_laying,
                                :t_weather_running, :t_temperature_running, :t_wind_speed_running, :t_wind_direction_running, :t_humidity_running,
                                :t_start_behavior, :t_consistency, :t_head_position, :t_pace, :t_indication,
                                :t_time_to_complete, :t_success_rate, :t_impression, :t_map_files,
                                :uuid, :update_time, :user_name, 'active'
                            )
                        """),
                        {
                            **session_data,
                            "uuid": new_uuid,
                            "update_time": get_current_update_time(),
                            "user_name": get_username()
                        }
                    )
                    
                    # Get the ID of the inserted row
                    result = conn.execute(
                        text("SELECT id FROM t_training_sessions WHERE t_session_number = :session_number AND t_dog_name = :dog_name"),
                        {"session_number": session_number, "dog_name": dog_name}
                    )
                    row = result.fetchone()
                    session_id = row[0] if row else None
                    
                    conn.commit()
                    self._restore_db_context(old_db_type)
                    return True, session_id, "Session saved successfully"
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            error_msg = f"Error saving session: {e}"
            print(error_msg)  # Print to console for debugging
            import traceback
            traceback.print_exc()  # Print full traceback
            return False, None, error_msg
    
    def load_trailing_session(self, session_number, dog_name):
        """
        Load a trailing session from the database
        
        Args:
            session_number: Session number to load
            dog_name: Dog name
            
        Returns:
            dict: Session data or None if not found
        """
        if not self._db_exists():
            return None
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                               t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                               t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                               t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                               t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                               t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                               t_time_to_complete, t_success_rate, t_impression, t_map_files,
                               uuid, update_time, status
                        FROM t_training_sessions
                        WHERE t_session_number = :session_number AND t_dog_name = :dog_name
                    """),
                    {"session_number": session_number, "dog_name": dog_name}
                )
                row = result.fetchone()
            
            self._restore_db_context(old_db_type)
            
            if row:
                return {
                    "id": row[0],
                    "t_session_number": row[1],
                    "t_dog_name": row[2],
                    "t_date": row[3],
                    "t_handler": row[4],
                    "t_field_support": row[5],
                    "t_location": row[6],
                    "t_start_time": row[7],
                    "t_finish_time": row[8],
                    "t_trail_age": row[9],
                    "t_trail_length": row[10],
                    "t_difficulty": row[11],
                    "t_trail_layer": row[12],
                    "t_cross_track_layer": row[13],
                    "t_cross_track_age": row[14],
                    "t_weather_laying": row[15],
                    "t_temperature_laying": row[16],
                    "t_wind_speed_laying": row[17],
                    "t_wind_direction_laying": row[18],
                    "t_humidity_laying": row[19],
                    "t_weather_running": row[20],
                    "t_temperature_running": row[21],
                    "t_wind_speed_running": row[22],
                    "t_wind_direction_running": row[23],
                    "t_humidity_running": row[24],
                    "t_start_behavior": row[25],
                    "t_consistency": row[26],
                    "t_head_position": row[27],
                    "t_pace": row[28],
                    "t_indication": row[29],
                    "t_time_to_complete": row[30],
                    "t_success_rate": row[31],
                    "t_impression": row[32],
                    "t_map_files": row[33],
                    "uuid": row[34],
                    "update_time": row[35],
                    "status": row[36]
                }
            return None
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error loading session: {e}")
            return None
    
    def delete_trailing_session(self, session_number, dog_name):
        """Delete a trailing session (set status to 'deleted')"""
        if not self._db_exists():
            return False
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                conn.execute(
                    text("UPDATE t_training_sessions SET status = 'deleted' WHERE t_session_number = :session_number AND t_dog_name = :dog_name"),
                    {"session_number": session_number, "dog_name": dog_name}
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error deleting session: {e}")
            return False
    
    def get_all_sessions_for_dog(self, dog_name, status_filter="Active", entry_type="Trailing"):
        """
        Get all sessions for a dog, optionally filtered by status
        
        Args:
            dog_name: Name of dog
            status_filter: "Active", "Deleted", "All", or "Both"
            entry_type: "Trailing" (ignored, kept for API compatibility)
            
        Returns:
            list of dicts with full session data
        """
        if not self._db_exists() or not dog_name:
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Normalize status_filter
                filter_lower = status_filter.lower() if status_filter else "active"
                
                if filter_lower == "active":
                    result = conn.execute(
                        text("""
                            SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                                   t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                                   t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                                   t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                                   t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                                   t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                                   t_time_to_complete, t_success_rate, t_impression, t_map_files,
                                   uuid, update_time, status
                            FROM t_training_sessions
                            WHERE t_dog_name = :dog_name AND (status = 'active' OR status IS NULL)
                            ORDER BY t_session_number
                        """),
                        {"dog_name": dog_name}
                    )
                elif filter_lower in ("deleted", "hidden"):
                    result = conn.execute(
                        text("""
                            SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                                   t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                                   t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                                   t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                                   t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                                   t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                                   t_time_to_complete, t_success_rate, t_impression, t_map_files,
                                   uuid, update_time, status
                            FROM t_training_sessions
                            WHERE t_dog_name = :dog_name AND status = 'deleted'
                            ORDER BY t_session_number
                        """),
                        {"dog_name": dog_name}
                    )
                else:  # "All" or "Both"
                    result = conn.execute(
                        text("""
                            SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                                   t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                                   t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                                   t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                                   t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                                   t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                                   t_time_to_complete, t_success_rate, t_impression, t_map_files,
                                   uuid, update_time, status
                            FROM t_training_sessions
                            WHERE t_dog_name = :dog_name
                            ORDER BY t_session_number
                        """),
                        {"dog_name": dog_name}
                    )
                
                rows = result.fetchall()
            
            self._restore_db_context(old_db_type)
            
            # Convert rows to dictionaries
            sessions = []
            for row in rows:
                sessions.append({
                    "id": row[0],
                    "t_session_number": row[1],
                    "t_dog_name": row[2],
                    "t_date": row[3],
                    "t_handler": row[4],
                    "t_field_support": row[5],
                    "t_location": row[6],
                    "t_start_time": row[7],
                    "t_finish_time": row[8],
                    "t_trail_age": row[9],
                    "t_trail_length": row[10],
                    "t_difficulty": row[11],
                    "t_trail_layer": row[12],
                    "t_cross_track_layer": row[13],
                    "t_cross_track_age": row[14],
                    "t_weather_laying": row[15],
                    "t_temperature_laying": row[16],
                    "t_wind_speed_laying": row[17],
                    "t_wind_direction_laying": row[18],
                    "t_humidity_laying": row[19],
                    "t_weather_running": row[20],
                    "t_temperature_running": row[21],
                    "t_wind_speed_running": row[22],
                    "t_wind_direction_running": row[23],
                    "t_humidity_running": row[24],
                    "t_start_behavior": row[25],
                    "t_consistency": row[26],
                    "t_head_position": row[27],
                    "t_pace": row[28],
                    "t_indication": row[29],
                    "t_time_to_complete": row[30],
                    "t_success_rate": row[31],
                    "t_impression": row[32],
                    "t_map_files": row[33],
                    "uuid": row[34],
                    "update_time": row[35],
                    "status": row[36]
                })
            
            return sessions
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error getting sessions: {e}")
            return []
    
    # ===== SELECTED TERRAINS =====
    
    def save_selected_terrains(self, session_id, terrain_list):
        """Save selected terrains for a trailing session"""
        if not self._db_exists() or not session_id:
            return
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Delete existing
                conn.execute(
                    text("DELETE FROM t_selected_terrains WHERE t_session_id = :session_id"),
                    {"session_id": session_id}
                )
                
                # Insert new
                for terrain in terrain_list:
                    if terrain.strip():
                        conn.execute(
                            text("""
                                INSERT INTO t_selected_terrains (t_session_id, terrain_name, user_name)
                                VALUES (:session_id, :terrain_name, :user_name)
                            """),
                            {"session_id": session_id, "terrain_name": terrain.strip(), "user_name": get_username()}
                        )
                
                conn.commit()
            
            self._restore_db_context(old_db_type)
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error saving terrains: {e}")
    
    def load_selected_terrains(self, session_id):
        """Load selected terrains for a trailing session"""
        if not self._db_exists() or not session_id:
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("SELECT terrain_name FROM t_selected_terrains WHERE t_session_id = :session_id ORDER BY terrain_name"),
                    {"session_id": session_id}
                )
                terrains = [row[0] for row in result.fetchall()]
            
            self._restore_db_context(old_db_type)
            return terrains
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            return []
    
    # ===== SELECTED PURPOSES =====
    
    def save_selected_purposes(self, session_id, purpose_list):
        """Save selected purposes for a trailing session"""
        if not self._db_exists() or not session_id:
            return
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Delete existing
                conn.execute(
                    text("DELETE FROM t_selected_purposes WHERE t_session_id = :session_id"),
                    {"session_id": session_id}
                )
                
                # Insert new
                for purpose in purpose_list:
                    if purpose.strip():
                        conn.execute(
                            text("""
                                INSERT INTO t_selected_purposes (t_session_id, purpose_name, user_name)
                                VALUES (:session_id, :purpose_name, :user_name)
                            """),
                            {"session_id": session_id, "purpose_name": purpose.strip(), "user_name": get_username()}
                        )
                
                conn.commit()
            
            self._restore_db_context(old_db_type)
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error saving purposes: {e}")
    
    def load_selected_purposes(self, session_id):
        """Load selected purposes for a trailing session"""
        if not self._db_exists() or not session_id:
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("SELECT purpose_name FROM t_selected_purposes WHERE t_session_id = :session_id ORDER BY purpose_name"),
                    {"session_id": session_id}
                )
                purposes = [row[0] for row in result.fetchall()]
            
            self._restore_db_context(old_db_type)
            return purposes
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            return []
    
    # ===== DISTRACTIONS =====
    
    def save_distractions(self, session_id, distractions_list):
        """
        Save distractions for a trailing session
        
        Args:
            session_id: Session ID
            distractions_list: List of dicts with 'type' and 'response' keys
        """
        if not self._db_exists() or not session_id:
            return
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                # Delete existing
                conn.execute(
                    text("DELETE FROM t_distractions WHERE t_session_id = :session_id"),
                    {"session_id": session_id}
                )
                
                # Insert new
                for distraction in distractions_list:
                    distraction_json = json.dumps(distraction)
                    conn.execute(
                        text("""
                            INSERT INTO t_distractions (t_session_id, distraction_data, user_name)
                            VALUES (:session_id, :distraction_data, :user_name)
                        """),
                        {"session_id": session_id, "distraction_data": distraction_json, "user_name": get_username()}
                    )
                
                conn.commit()
            
            self._restore_db_context(old_db_type)
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error saving distractions: {e}")
    
    def load_distractions(self, session_id):
        """Load distractions for a trailing session"""
        if not self._db_exists() or not session_id:
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            with get_connection() as conn:
                result = conn.execute(
                    text("SELECT distraction_data FROM t_distractions WHERE t_session_id = :session_id"),
                    {"session_id": session_id}
                )
                distractions = []
                for row in result.fetchall():
                    try:
                        distractions.append(json.loads(row[0]))
                    except:
                        pass
            
            self._restore_db_context(old_db_type)
            return distractions
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            return []
    
    def update_session_status(self, session_number, dog_name, new_status):
        """Update session status (active/deleted)
        
        Args:
            session_number: Session number to update
            dog_name: Dog name for the session
            new_status: 'active' or 'deleted'
        
        Returns:
            True if successful, False otherwise
        """
        import traceback
        from sqlalchemy import text
        from database import get_connection
        
        old_db_type = self._switch_db_context()
        
        try:
            with get_connection() as conn:
                conn.execute(
                    text("""
                        UPDATE t_training_sessions 
                        SET status = :status, update_time = :update_time
                        WHERE t_session_number = :session_number AND t_dog_name = :dog_name
                    """),
                    {
                        "status": new_status,
                        "update_time": datetime.now(),
                        "session_number": session_number,
                        "dog_name": dog_name
                    }
                )
                conn.commit()
            
            self._restore_db_context(old_db_type)
            return True
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error updating session status: {e}")
            traceback.print_exc()
            return False
    
    def get_trailing_sessions_for_export(self, dog_name, range_type, start_value, end_value, sort_order, status_filter):
        """
        Get trailing sessions for PDF export.
        
        Args:
            dog_name: Name of dog
            range_type: "Date" or "Session"
            start_value: Start date or session number
            end_value: End date or session number
            sort_order: "Ascending" or "Descending"
            status_filter: "active", "deleted", or "both"
            
        Returns:
            list of session dictionaries
        """
        if not self._db_exists() or not dog_name:
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            # Build status filter clause
            if status_filter == "active":
                status_clause = " AND (status = 'active' OR status IS NULL)"
            elif status_filter == "deleted":
                status_clause = " AND status = 'deleted'"
            else:  # "both"
                status_clause = ""
            
            # Build order clause
            if range_type == "Date":
                order_clause = "t_date ASC, t_session_number ASC" if sort_order == "Ascending" else "t_date DESC, t_session_number DESC"
            else:
                order_clause = "t_session_number ASC" if sort_order == "Ascending" else "t_session_number DESC"
            
            with get_connection() as conn:
                if range_type == "Date":
                    query = text(f"""
                        SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                               t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                               t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                               t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                               t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                               t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                               t_time_to_complete, t_success_rate, t_impression, t_map_files,
                               uuid, update_time, status
                        FROM t_training_sessions
                        WHERE t_dog_name = :dog_name
                          AND t_date >= :start_value
                          AND t_date <= :end_value{status_clause}
                        ORDER BY {order_clause}
                    """)
                    result = conn.execute(query, {
                        "dog_name": dog_name,
                        "start_value": start_value,
                        "end_value": end_value
                    })
                else:  # Session
                    query = text(f"""
                        SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                               t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                               t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                               t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                               t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                               t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                               t_time_to_complete, t_success_rate, t_impression, t_map_files,
                               uuid, update_time, status
                        FROM t_training_sessions
                        WHERE t_dog_name = :dog_name
                          AND t_session_number >= :start_value
                          AND t_session_number <= :end_value{status_clause}
                        ORDER BY {order_clause}
                    """)
                    result = conn.execute(query, {
                        "dog_name": dog_name,
                        "start_value": int(start_value),
                        "end_value": int(end_value)
                    })
                
                sessions = []
                for row in result.fetchall():
                    session_id = row[0]
                    
                    # Fetch session purposes
                    try:
                        purpose_result = conn.execute(
                            text("SELECT purpose_name FROM t_selected_purposes WHERE t_session_id = :session_id ORDER BY purpose_name"),
                            {"session_id": session_id}
                        )
                        purposes = [p[0] for p in purpose_result.fetchall()]
                    except Exception:
                        purposes = []
                    
                    # Fetch terrains
                    try:
                        terrain_result = conn.execute(
                            text("SELECT terrain_name FROM t_selected_terrains WHERE t_session_id = :session_id ORDER BY terrain_name"),
                            {"session_id": session_id}
                        )
                        terrains = [t[0] for t in terrain_result.fetchall()]
                    except Exception:
                        terrains = []
                    
                    # Fetch distractions
                    try:
                        distraction_result = conn.execute(
                            text("SELECT distraction_data FROM t_distractions WHERE t_session_id = :session_id"),
                            {"session_id": session_id}
                        )
                        distraction_rows = distraction_result.fetchall()
                        distractions = []
                        for d_row in distraction_rows:
                            if d_row[0]:
                                try:
                                    import json
                                    d_data = json.loads(d_row[0])
                                    if isinstance(d_data, list):
                                        distractions.extend(d_data)
                                    else:
                                        distractions.append(d_data)
                                except (json.JSONDecodeError, ValueError):
                                    # Try ast.literal_eval for Python dict strings (single quotes)
                                    try:
                                        import ast
                                        d_data = ast.literal_eval(d_row[0])
                                        if isinstance(d_data, list):
                                            distractions.extend(d_data)
                                        else:
                                            distractions.append(d_data)
                                    except (ValueError, SyntaxError):
                                        # Just append the raw string
                                        distractions.append(d_row[0])
                    except Exception:
                        distractions = []
                    
                    session = {
                        'id': session_id,
                        't_session_number': row[1],
                        't_dog_name': row[2],
                        't_date': row[3],
                        't_handler': row[4],
                        't_field_support': row[5],
                        't_location': row[6],
                        't_start_time': row[7],
                        't_finish_time': row[8],
                        't_trail_age': row[9],
                        't_trail_length': row[10],
                        't_difficulty': row[11],
                        't_trail_layer': row[12],
                        't_cross_track_layer': row[13],
                        't_cross_track_age': row[14],
                        't_weather_laying': row[15],
                        't_temperature_laying': row[16],
                        't_wind_speed_laying': row[17],
                        't_wind_direction_laying': row[18],
                        't_humidity_laying': row[19],
                        't_weather_running': row[20],
                        't_temperature_running': row[21],
                        't_wind_speed_running': row[22],
                        't_wind_direction_running': row[23],
                        't_humidity_running': row[24],
                        't_start_behavior': row[25],
                        't_consistency': row[26],
                        't_head_position': row[27],
                        't_pace': row[28],
                        't_indication': row[29],
                        't_time_to_complete': row[30],
                        't_success_rate': row[31],
                        't_impression': row[32],
                        't_map_files': row[33],
                        'uuid': row[34],
                        'update_time': row[35],
                        'status': row[36],
                        'purposes': purposes,
                        'terrains': terrains,
                        'distractions': distractions
                    }
                    sessions.append(session)
            
            self._restore_db_context(old_db_type)
            return sessions
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error getting sessions for export: {e}")
            traceback.print_exc()
            return []
    
    def get_trailing_sessions_by_numbers(self, dog_name, session_numbers):
        """
        Get trailing sessions by specific session numbers for PDF export.
        
        Args:
            dog_name: Name of dog
            session_numbers: List of session numbers to fetch
            
        Returns:
            list of session dictionaries
        """
        if not self._db_exists() or not dog_name or not session_numbers:
            return []
        
        try:
            old_db_type = self._switch_db_context()
            
            sessions = []
            # Sort session numbers for consistent output
            sorted_numbers = sorted(session_numbers)
            
            with get_connection() as conn:
                for session_num in sorted_numbers:
                    query = text("""
                        SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                               t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                               t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                               t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                               t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                               t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                               t_time_to_complete, t_success_rate, t_impression, t_map_files,
                               uuid, update_time, status
                        FROM t_training_sessions
                        WHERE t_dog_name = :dog_name AND t_session_number = :session_num
                    """)
                    result = conn.execute(query, {
                        "dog_name": dog_name,
                        "session_num": session_num
                    })
                    
                    row = result.fetchone()
                    if row:
                        session_id = row[0]
                        
                        # Fetch session purposes
                        try:
                            purpose_result = conn.execute(
                                text("SELECT purpose_name FROM t_selected_purposes WHERE t_session_id = :session_id ORDER BY purpose_name"),
                                {"session_id": session_id}
                            )
                            purposes = [p[0] for p in purpose_result.fetchall()]
                        except Exception:
                            purposes = []
                        
                        # Fetch terrains
                        try:
                            terrain_result = conn.execute(
                                text("SELECT terrain_name FROM t_selected_terrains WHERE t_session_id = :session_id ORDER BY terrain_name"),
                                {"session_id": session_id}
                            )
                            terrains = [t[0] for t in terrain_result.fetchall()]
                        except Exception:
                            terrains = []
                        
                        # Fetch distractions
                        try:
                            distraction_result = conn.execute(
                                text("SELECT distraction_data FROM t_distractions WHERE t_session_id = :session_id"),
                                {"session_id": session_id}
                            )
                            distraction_rows = distraction_result.fetchall()
                            distractions = []
                            for d_row in distraction_rows:
                                if d_row[0]:
                                    try:
                                        d_data = json.loads(d_row[0])
                                        if isinstance(d_data, list):
                                            distractions.extend(d_data)
                                        else:
                                            distractions.append(d_data)
                                    except (json.JSONDecodeError, ValueError):
                                        try:
                                            import ast
                                            d_data = ast.literal_eval(d_row[0])
                                            if isinstance(d_data, list):
                                                distractions.extend(d_data)
                                            else:
                                                distractions.append(d_data)
                                        except (ValueError, SyntaxError):
                                            distractions.append(d_row[0])
                        except Exception:
                            distractions = []
                        
                        session = {
                            'id': session_id,
                            't_session_number': row[1],
                            't_dog_name': row[2],
                            't_date': row[3],
                            't_handler': row[4],
                            't_field_support': row[5],
                            't_location': row[6],
                            't_start_time': row[7],
                            't_finish_time': row[8],
                            't_trail_age': row[9],
                            't_trail_length': row[10],
                            't_difficulty': row[11],
                            't_trail_layer': row[12],
                            't_cross_track_layer': row[13],
                            't_cross_track_age': row[14],
                            't_weather_laying': row[15],
                            't_temp_laying': row[16],
                            't_wind_laying': row[17],
                            't_wind_direction_laying': row[18],
                            't_humidity_laying': row[19],
                            't_weather_running': row[20],
                            't_temp_running': row[21],
                            't_wind_running': row[22],
                            't_wind_direction_running': row[23],
                            't_humidity_running': row[24],
                            't_start_behavior': row[25],
                            't_consistency': row[26],
                            't_head_pos': row[27],
                            't_pace': row[28],
                            't_indication': row[29],
                            't_time': row[30],
                            't_success': row[31],
                            't_impression': row[32],
                            't_map_files': row[33],
                            'uuid': row[34],
                            'update_time': row[35],
                            'status': row[36],
                            'purposes': purposes,
                            'terrains': terrains,
                            'distractions': distractions
                        }
                        sessions.append(session)
            
            self._restore_db_context(old_db_type)
            return sessions
            
        except Exception as e:
            self._restore_db_context(old_db_type)
            print(f"Error getting sessions by numbers: {e}")
            import traceback
            traceback.print_exc()
            return []


# Singleton database manager
_db_manager = None

def get_db_manager():
    """Get the singleton database manager"""
    global _db_manager
    if _db_manager is None:
        import sv
        _db_manager = DatabaseManager(sv.db_type.get())
    return _db_manager


class DatabaseOperations:
    """Database operations for trailing UI - provides interface between UI and DatabaseManager"""
    
    def __init__(self, ui):
        self.ui = ui
        self.db_manager = get_db_manager()
    
    def save_db_setting(self, key, value):
        """Save setting to database"""
        self.db_manager.save_setting(key, value)
    
    def load_db_setting(self, key, default=None):
        """Load setting from database"""
        return self.db_manager.load_setting(key, default)
    
    def get_next_session_number(self, dog_name=None):
        """Get next session number for a dog"""
        import sv
        if dog_name is None:
            dog_name = sv.t_dog.get()
        return self.db_manager.get_next_session_number(dog_name)
    
    def save_session(self, session_data, is_update=False):
        """Save or update a trailing session"""
        return self.db_manager.save_trailing_session(session_data, is_update)
    
    def load_session(self, session_number, dog_name):
        """Load a trailing session"""
        return self.db_manager.load_trailing_session(session_number, dog_name)
    
    def delete_session(self, session_number, dog_name):
        """Delete a trailing session"""
        return self.db_manager.delete_trailing_session(session_number, dog_name)
    
    def get_all_sessions_for_dog(self, dog_name, status_filter="Active", entry_type="Trailing"):
        """Get all sessions for a dog"""
        return self.db_manager.get_all_sessions_for_dog(dog_name, status_filter, entry_type)
    
    def save_selected_terrains(self, session_id, terrain_list):
        """Save selected terrains"""
        self.db_manager.save_selected_terrains(session_id, terrain_list)
    
    def load_selected_terrains(self, session_id):
        """Load selected terrains"""
        return self.db_manager.load_selected_terrains(session_id)
    
    def save_selected_purposes(self, session_id, purpose_list):
        """Save selected purposes"""
        self.db_manager.save_selected_purposes(session_id, purpose_list)
    
    def load_selected_purposes(self, session_id):
        """Load selected purposes"""
        return self.db_manager.load_selected_purposes(session_id)
    
    def save_distractions(self, session_id, distractions_list):
        """Save distractions"""
        self.db_manager.save_distractions(session_id, distractions_list)
    
    def load_distractions(self, session_id):
        """Load distractions"""
        return self.db_manager.load_distractions(session_id)
    
    def update_session_status(self, session_number, dog_name, new_status):
        """Update session status (active/deleted)"""
        return self.db_manager.update_session_status(session_number, dog_name, new_status)
    
    def get_trailing_sessions_for_export(self, dog_name, range_type, start_value, end_value, sort_order, status_filter):
        """Get sessions for PDF export"""
        return self.db_manager.get_trailing_sessions_for_export(
            dog_name, range_type, start_value, end_value, sort_order, status_filter
        )
    
    def get_trailing_sessions_by_numbers(self, dog_name, session_numbers):
        """Get specific sessions by session numbers for PDF export"""
        return self.db_manager.get_trailing_sessions_by_numbers(dog_name, session_numbers)
