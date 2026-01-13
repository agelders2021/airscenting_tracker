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
Backup Management Module for Air-Scenting Logger

Provides shared utilities for backup operations:
- UUID generation for session tracking
- Update time management
- Sync operations between database and JSON folders

This module is designed to be shared between Airscent and Trailing tabs.

Author: AI Assistant
Date: 2025-01-07
"""

import uuid
import json
import shutil
import threading
from datetime import datetime
from pathlib import Path


def generate_session_uuid():
    """
    Generate a unique UUID for a new session.
    
    This UUID is used to track sessions across the database and JSON backup files,
    enabling synchronization between primary and secondary backup locations.
    
    Returns:
        str: A new UUID4 string (e.g., 'a1b2c3d4-e5f6-7890-abcd-ef1234567890')
    
    Note:
        - UUID should only be generated when creating a NEW session (Save Session)
        - UUID should NOT be regenerated when updating an existing session (Update Session)
    """
    return str(uuid.uuid4())


def get_current_update_time():
    """
    Get the current datetime for update_time field.
    
    Returns:
        datetime: Current UTC datetime
        
    Note:
        This should be called on EVERY save or update operation.
    """
    return datetime.utcnow()


def get_update_time_iso():
    """
    Get the current datetime as ISO format string for JSON serialization.
    
    Returns:
        str: Current datetime in ISO format (e.g., '2025-01-07T14:30:00.123456')
    """
    return datetime.utcnow().isoformat()


# ============================================================================
# SYNC UTILITIES
# ============================================================================

def _format_update_time(update_time):
    """
    Safely format update_time to ISO string.
    Handles both datetime objects and strings.
    """
    if not update_time:
        return ""
    if isinstance(update_time, str):
        return update_time
    try:
        return update_time.isoformat()
    except:
        return str(update_time)


def _parse_update_time(update_time_str):
    """
    Safely parse update_time string to datetime.
    Returns None if parsing fails.
    """
    if not update_time_str:
        return None
    if isinstance(update_time_str, datetime):
        return update_time_str
    try:
        return datetime.fromisoformat(update_time_str)
    except:
        return None


class BackupSyncManager:
    """
    Manages synchronization between database and JSON backup folders.
    
    Handles:
    - Startup sync between DB, primary JSON, and secondary JSON
    - Background thread execution
    - Blocking Edit/Hide operations during sync
    """
    
    def __init__(self):
        self.sync_in_progress = False
        self.sync_thread = None
        self.sync_results = {
            "db_to_json": 0,
            "json_to_db": 0,
            "primary_to_secondary": 0,
            "secondary_to_primary": 0,
            "errors": []
        }
    
    def is_sync_in_progress(self):
        """Check if sync is currently running"""
        return self.sync_in_progress
    
    def start_background_sync(self, db_type, primary_folder, secondary_folder, 
                               on_complete=None, status_callback=None):
        """
        Start background sync in a separate thread.
        
        Args:
            db_type: Database type (sqlite, postgres, etc.)
            primary_folder: Path to primary JSON folder
            secondary_folder: Path to secondary JSON folder (can be None)
            on_complete: Callback function when sync completes (receives sync_results)
            status_callback: Callback to update status bar (receives message string)
        """
        if self.sync_in_progress:
            print("Sync already in progress")
            return False
        
        self.sync_in_progress = True
        self.sync_results = {
            "db_to_json": 0,
            "json_to_db": 0,
            "primary_to_secondary": 0,
            "secondary_to_primary": 0,
            "errors": []
        }
        
        def sync_worker():
            try:
                if status_callback:
                    status_callback("Sync: Scanning JSON folders...")
                
                import time
                self._run_sync(db_type, primary_folder, secondary_folder, status_callback)
                
            except Exception as e:
                self.sync_results["errors"].append(f"Sync error: {e}")
                print(f"Sync error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.sync_in_progress = False
                if on_complete:
                    on_complete(self.sync_results)
        
        self.sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self.sync_thread.start()
        return True
    
    def _run_sync(self, db_type, primary_folder, secondary_folder, status_callback):
        """
        Main sync logic - runs in background thread.
        
        Sync order:
        1. Scan primary JSON folder
        2. Scan secondary JSON folder (if exists)
        3. Get DB sessions with UUID/update_time
        4. Sync DB â†’ Primary JSON (DB newer or missing in JSON)
        5. Sync Primary JSON â†’ DB (JSON newer)
        6. Sync Primary â†’ Secondary (Primary newer or missing)
        7. Sync Secondary â†’ Primary (Secondary newer, also update DB)
        """
        primary_path = Path(primary_folder) if primary_folder else None
        secondary_path = Path(secondary_folder) if secondary_folder else None
        
        # Step 1: Scan primary JSON folder
        primary_dict = {}
        if primary_path and primary_path.exists():
            if status_callback:
                status_callback("Sync: Scanning primary JSON folder...")
            primary_dict = scan_json_folder(primary_path)
            print(f"Sync: Found {len(primary_dict)} sessions in primary JSON")
        
        # Step 2: Scan secondary JSON folder
        secondary_dict = {}
        if secondary_path and secondary_path.exists():
            if status_callback:
                status_callback("Sync: Scanning secondary JSON folder...")
            secondary_dict = scan_json_folder(secondary_path)
            print(f"Sync: Found {len(secondary_dict)} sessions in secondary JSON")
        
        # Step 3: Get DB sessions
        if status_callback:
            status_callback("Sync: Reading database sessions...")
        db_sessions = get_db_sessions_for_sync(db_type)
        print(f"Sync: Found {len(db_sessions)} sessions in database")
        
        # Step 4: Sync DB â†’ Primary JSON
        if primary_path and primary_path.exists():
            if status_callback:
                status_callback("Sync: Updating JSON from database...")
            count = sync_db_to_json(db_sessions, primary_dict, primary_path, db_type)
            self.sync_results["db_to_json"] = count
            if count > 0:
                # Re-scan primary after updates
                primary_dict = scan_json_folder(primary_path)
        
        # Step 5: Sync Primary JSON â†’ DB
        if primary_dict:
            if status_callback:
                status_callback("Sync: Updating database from JSON...")
            count = sync_json_to_db(primary_dict, db_sessions, db_type)
            self.sync_results["json_to_db"] = count
        
        # Step 6: Sync Primary â†’ Secondary
        if secondary_path and secondary_path.exists() and primary_dict:
            if status_callback:
                status_callback("Sync: Mirroring to secondary backup...")
            count = sync_primary_to_secondary(primary_dict, secondary_dict, secondary_path)
            self.sync_results["primary_to_secondary"] = count
        
        # Step 7: Sync Secondary â†’ Primary (and DB)
        if secondary_path and secondary_path.exists() and primary_path and primary_path.exists():
            if status_callback:
                status_callback("Sync: Checking secondary for newer files...")
            # Re-scan primary to get current state
            primary_dict = scan_json_folder(primary_path)
            count = sync_secondary_to_primary(secondary_dict, primary_dict, primary_path, db_type)
            self.sync_results["secondary_to_primary"] = count
        
        print(f"Sync complete: {self.sync_results}")


def scan_json_folder(folder_path):
    """
    Scan a JSON folder and build a dictionary of sessions by UUID.
    
    Args:
        folder_path: Path to JSON folder
        
    Returns:
        dict: {uuid: {"update_time": datetime, "file_mtime": datetime, "filepath": Path, "data": dict}}
              Sessions without UUID are indexed by filename
    """
    result = {}
    folder = Path(folder_path)
    
    if not folder.exists():
        return result
    
    for json_file in folder.glob("*session*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            session_uuid = data.get("uuid")
            update_time_str = data.get("update_time")
            
            # Parse update_time from JSON
            update_time = None
            if update_time_str:
                try:
                    update_time = datetime.fromisoformat(update_time_str)
                except:
                    pass
            
            # Get file modification time as fallback
            file_mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
            
            # If no update_time in JSON, use file modification time
            if update_time is None:
                update_time = file_mtime
            
            # Use UUID as key if available, otherwise use filename
            key = session_uuid if session_uuid else json_file.stem
            
            result[key] = {
                "update_time": update_time,
                "file_mtime": file_mtime,
                "filepath": json_file,
                "data": data,
                "has_uuid": bool(session_uuid)
            }
            
        except Exception as e:
            print(f"Warning: Could not read {json_file}: {e}")
    
    return result


def get_db_sessions_for_sync(db_type):
    """
    Get all sessions from database with UUID and update_time.
    Includes both airscenting (training_sessions) and trailing (t_training_sessions) tables.
    
    Returns:
        dict: {uuid: {"update_time": datetime, "session_number": int, "dog_name": str, "data": dict}}
    """
    result = {}
    
    try:
        import config
        from sqlalchemy import text
        
        # Temporarily switch to correct DB type
        old_db_type = config.DB_TYPE
        config.DB_TYPE = db_type
        
        from database import engine, get_connection
        from importlib import reload
        import database
        
        if old_db_type != db_type:
            engine.dispose()
            reload(database)
        
        with database.get_connection() as conn:
            # Get airscenting sessions
            query = text("""
                SELECT id, session_number, dog_name, date, handler, session_purpose, 
                       field_support, location, search_area_size, num_subjects, 
                       handler_knowledge, weather, temperature, wind_direction, 
                       wind_speed, search_type, drive_level, subjects_found, 
                       comments, image_files, entry_type, update_time, uuid
                FROM training_sessions
                WHERE uuid IS NOT NULL AND uuid != ''
            """)
            rows = conn.execute(query).fetchall()
            
            for row in rows:
                session_uuid = row[22]  # uuid column
                update_time_raw = row[21]   # update_time column
                
                # Parse update_time to datetime object for consistent comparison
                update_time = _parse_update_time(update_time_raw)
                
                if session_uuid:
                    result[session_uuid] = {
                        "update_time": update_time,
                        "session_number": row[1],
                        "dog_name": row[2],
                        "data": {
                            "id": row[0],
                            "session_number": row[1],
                            "dog_name": row[2],
                            "date": str(row[3]) if row[3] else "",
                            "handler": row[4] or "",
                            "session_purpose": row[5] or "",
                            "field_support": row[6] or "",
                            "location": row[7] or "",
                            "search_area_size": row[8] or "",
                            "num_subjects": row[9] or "",
                            "handler_knowledge": row[10] or "",
                            "weather": row[11] or "",
                            "temperature": row[12] or "",
                            "wind_direction": row[13] or "",
                            "wind_speed": row[14] or "",
                            "search_type": row[15] or "",
                            "drive_level": row[16] or "",
                            "subjects_found": row[17] or "",
                            "comments": row[18] or "",
                            "image_files": row[19] or "",
                            "entry_type": row[20] or "",
                            "update_time": _format_update_time(update_time),
                            "uuid": session_uuid
                        }
                    }
            
            # Get trailing sessions
            try:
                t_query = text("""
                    SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                           t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                           t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                           t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                           t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                           t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                           t_time_to_complete, t_success_rate, t_impression, t_map_files,
                           update_time, uuid
                    FROM t_training_sessions
                    WHERE uuid IS NOT NULL AND uuid != ''
                """)
                t_rows = conn.execute(t_query).fetchall()
                
                for row in t_rows:
                    session_uuid = row[35]  # uuid column
                    update_time_raw = row[34]   # update_time column
                    
                    update_time = _parse_update_time(update_time_raw)
                    
                    if session_uuid:
                        result[session_uuid] = {
                            "update_time": update_time,
                            "session_number": row[1],
                            "dog_name": row[2],
                            "data": {
                                "id": row[0],
                                "t_session_number": row[1],
                                "t_dog_name": row[2],
                                "t_date": str(row[3]) if row[3] else "",
                                "t_handler": row[4] or "",
                                "t_field_support": row[5] or "",
                                "t_location": row[6] or "",
                                "t_start_time": row[7] or "",
                                "t_finish_time": row[8] or "",
                                "t_trail_age": row[9] or "",
                                "t_trail_length": row[10] or "",
                                "t_difficulty": row[11] or "",
                                "t_trail_layer": row[12] or "",
                                "t_cross_track_layer": row[13] or "",
                                "t_cross_track_age": row[14] or "",
                                "t_weather_laying": row[15] or "",
                                "t_temperature_laying": row[16] or "",
                                "t_wind_speed_laying": row[17] or "",
                                "t_wind_direction_laying": row[18] or "",
                                "t_humidity_laying": row[19] or "",
                                "t_weather_running": row[20] or "",
                                "t_temperature_running": row[21] or "",
                                "t_wind_speed_running": row[22] or "",
                                "t_wind_direction_running": row[23] or "",
                                "t_humidity_running": row[24] or "",
                                "t_start_behavior": row[25] or "",
                                "t_consistency": row[26] or "",
                                "t_head_position": row[27] or "",
                                "t_pace": row[28] or "",
                                "t_indication": row[29] or "",
                                "t_time_to_complete": row[30] or "",
                                "t_success_rate": row[31] or "",
                                "t_impression": row[32] or "",
                                "t_map_files": row[33] or "",
                                "update_time": _format_update_time(update_time),
                                "uuid": session_uuid
                            }
                        }
            except Exception as te:
                # t_training_sessions table might not exist
                print(f"Note: Could not query t_training_sessions: {te}")
        
        # Restore original DB type
        if old_db_type != db_type:
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
    except Exception as e:
        print(f"Error getting DB sessions for sync: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def sync_db_to_json(db_sessions, json_dict, json_folder, db_type):
    """
    Sync database to JSON - create/update JSON files for DB entries.
    Uses file modification time for comparison (handles manual edits).
    
    Args:
        db_sessions: Dict from get_db_sessions_for_sync()
        json_dict: Dict from scan_json_folder()
        json_folder: Path to JSON folder
        db_type: Database type
        
    Returns:
        int: Number of files created/updated
    """
    import re
    count = 0
    
    for session_uuid, db_info in db_sessions.items():
        json_info = json_dict.get(session_uuid)
        
        should_write = False
        
        if not json_info:
            # Session not in JSON - create it
            should_write = True
            print(f"Sync: DB session {session_uuid} not in JSON, creating...")
        else:
            # Compare DB update time with JSON file modification time
            db_time = _parse_update_time(db_info["update_time"])
            # Use file modification time (handles manual edits)
            json_time = json_info.get("file_mtime") or _parse_update_time(json_info.get("update_time"))
            
            if db_time and json_time and db_time > json_time:
                should_write = True
                print(f"Sync: DB newer than JSON file for {session_uuid}")
        
        if should_write:
            try:
                # Load related data (terrains, responses) from DB
                session_data = load_full_session_from_db(
                    db_info["session_number"], 
                    db_info["dog_name"], 
                    db_type
                )
                
                if session_data:
                    # Create filename
                    dog_name = session_data.get("dog_name", "unknown")
                    safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
                    session_num = session_data.get("session_number")
                    date_str = session_data.get("date", "").replace("-", "")
                    filename = f"{safe_dog_name}_session_{session_num}_{date_str}.json"
                    
                    # Add backup timestamp
                    session_data["backup_timestamp"] = datetime.now().isoformat()
                    
                    # Write JSON
                    filepath = Path(json_folder) / filename
                    with open(filepath, 'w') as f:
                        json.dump(session_data, f, indent=2, default=str)
                    
                    count += 1
                    print(f"Sync: Wrote {filepath}")
                    
            except Exception as e:
                print(f"Sync error writing JSON for {session_uuid}: {e}")
    
    return count


def load_full_session_from_db(session_number, dog_name, db_type):
    """Load complete session data including terrains and responses from DB."""
    try:
        import config
        from sqlalchemy import text
        
        old_db_type = config.DB_TYPE
        config.DB_TYPE = db_type
        
        from database import engine, get_connection
        from importlib import reload
        import database
        
        if old_db_type != db_type:
            engine.dispose()
            reload(database)
        
        session_data = None
        
        with database.get_connection() as conn:
            # Get main session
            result = conn.execute(
                text("""
                    SELECT id, date, handler, session_purpose, field_support, dog_name, 
                           location, search_area_size, num_subjects, handler_knowledge, 
                           weather, temperature, wind_direction, wind_speed, search_type, 
                           drive_level, subjects_found, comments, image_files, 
                           entry_type, update_time, uuid, status
                    FROM training_sessions 
                    WHERE session_number = :session_number AND dog_name = :dog_name
                """),
                {"session_number": session_number, "dog_name": dog_name}
            )
            row = result.fetchone()
            
            if row:
                session_id = row[0]
                session_data = {
                    "session_number": session_number,
                    "date": str(row[1]) if row[1] else "",
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
                    "image_files": json.loads(row[18]) if row[18] else [],
                    "entry_type": row[19] or "",
                    "update_time": _format_update_time(row[20]),
                    "uuid": row[21] or "",
                    "status": row[22] or "active"
                }
                
                # Get terrains
                terrain_result = conn.execute(
                    text("SELECT terrain_name FROM selected_terrains WHERE session_id = :session_id"),
                    {"session_id": session_id}
                )
                session_data["selected_terrains"] = [r[0] for r in terrain_result]
                
                # Get subject responses
                response_result = conn.execute(
                    text("""
                        SELECT subject_number, tfr, refind 
                        FROM subject_responses 
                        WHERE session_id = :session_id 
                        ORDER BY subject_number
                    """),
                    {"session_id": session_id}
                )
                session_data["subject_responses"] = [
                    {"subject_number": r[0], "tfr": r[1] or "", "refind": r[2] or ""}
                    for r in response_result
                ]
        
        # Restore original DB type
        if old_db_type != db_type:
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
        
        return session_data
        
    except Exception as e:
        print(f"Error loading full session from DB: {e}")
        return None


def sync_json_to_db(json_dict, db_sessions, db_type):
    """
    Sync JSON to database - create missing or update DB entries where JSON is newer.
    Uses file modification time for comparison (handles manual edits).
    
    Returns:
        int: Number of DB records created/updated
    """
    count = 0
    
    for key, json_info in json_dict.items():
        if not json_info.get("has_uuid"):
            continue  # Skip files without UUID
        
        session_uuid = key
        db_info = db_sessions.get(session_uuid)
        
        if not db_info:
            # Session exists in JSON but NOT in DB - create it
            print(f"Sync: Session {session_uuid} in JSON but not in DB, creating...")
            try:
                if insert_session_from_json(json_info["data"], db_type):
                    count += 1
            except Exception as e:
                print(f"Sync error inserting session from JSON: {e}")
        else:
            # Both exist - check if JSON file is newer (use file mtime for manual edits)
            db_time = _parse_update_time(db_info["update_time"])
            # Use file modification time, falling back to update_time from JSON
            json_time = json_info.get("file_mtime") or _parse_update_time(json_info.get("update_time"))
            
            if db_time and json_time and json_time > db_time:
                print(f"Sync: JSON file newer than DB for {session_uuid}, updating DB...")
                try:
                    if update_db_from_json(json_info["data"], db_type):
                        count += 1
                except Exception as e:
                    print(f"Sync error updating DB from JSON: {e}")
    
    return count
    
    return count


def insert_session_from_json(json_data, db_type):
    """Insert a new session into database from JSON data.
    
    Automatically detects whether it's an airscenting or trailing session
    based on the presence of 't_session_number' key.
    """
    # Detect session type
    is_trailing = 't_session_number' in json_data
    
    if is_trailing:
        return insert_trailing_session_from_json(json_data, db_type)
    else:
        return insert_airscenting_session_from_json(json_data, db_type)


def insert_airscenting_session_from_json(json_data, db_type):
    """Insert a new airscenting session into database from JSON data."""
    try:
        import config
        from sqlalchemy import text
        from ui_utils import get_username
        
        old_db_type = config.DB_TYPE
        config.DB_TYPE = db_type
        
        from database import engine, get_connection
        from importlib import reload
        import database
        
        if old_db_type != db_type:
            engine.dispose()
            reload(database)
        
        with database.get_connection() as conn:
            image_files = json_data.get("image_files", [])
            if isinstance(image_files, list):
                image_files_json = json.dumps(image_files)
            else:
                image_files_json = image_files or ""
            
            # Check if session already exists (by session_number + dog_name)
            check_result = conn.execute(
                text("""
                    SELECT id FROM training_sessions 
                    WHERE session_number = :session_number AND dog_name = :dog_name
                """),
                {
                    "session_number": json_data.get("session_number"),
                    "dog_name": json_data.get("dog_name")
                }
            )
            existing = check_result.fetchone()
            
            if existing:
                # Session exists with same number/dog but different UUID - update it
                print(f"Sync: Session {json_data.get('session_number')}/{json_data.get('dog_name')} exists, updating with UUID...")
                conn.execute(
                    text("""
                        UPDATE training_sessions SET
                            date = :date,
                            handler = :handler,
                            session_purpose = :session_purpose,
                            field_support = :field_support,
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
                            entry_type = :entry_type,
                            update_time = :update_time,
                            uuid = :uuid,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE session_number = :session_number AND dog_name = :dog_name
                    """),
                    {
                        "date": json_data.get("date"),
                        "handler": json_data.get("handler"),
                        "session_purpose": json_data.get("session_purpose"),
                        "field_support": json_data.get("field_support"),
                        "location": json_data.get("location"),
                        "search_area_size": json_data.get("search_area_size"),
                        "num_subjects": json_data.get("num_subjects"),
                        "handler_knowledge": json_data.get("handler_knowledge"),
                        "weather": json_data.get("weather"),
                        "temperature": json_data.get("temperature"),
                        "wind_direction": json_data.get("wind_direction"),
                        "wind_speed": json_data.get("wind_speed"),
                        "search_type": json_data.get("search_type"),
                        "drive_level": json_data.get("drive_level"),
                        "subjects_found": json_data.get("subjects_found"),
                        "comments": json_data.get("comments"),
                        "image_files": image_files_json,
                        "entry_type": json_data.get("entry_type"),
                        "update_time": json_data.get("update_time"),
                        "uuid": json_data.get("uuid"),
                        "session_number": json_data.get("session_number"),
                        "dog_name": json_data.get("dog_name")
                    }
                )
            else:
                # Insert new session
                conn.execute(
                    text("""
                        INSERT INTO training_sessions 
                        (date, session_number, handler, session_purpose, field_support, dog_name, 
                         location, search_area_size, num_subjects, handler_knowledge, 
                         weather, temperature, wind_direction, wind_speed, search_type, 
                         drive_level, subjects_found, comments, image_files, 
                         entry_type, update_time, uuid, user_name, status)
                        VALUES (:date, :session_number, :handler, :session_purpose, :field_support, :dog_name,
                                :location, :search_area_size, :num_subjects, :handler_knowledge,
                                :weather, :temperature, :wind_direction, :wind_speed, :search_type,
                                :drive_level, :subjects_found, :comments, :image_files,
                                :entry_type, :update_time, :uuid, :user_name, :status)
                    """),
                    {
                        "date": json_data.get("date"),
                        "session_number": json_data.get("session_number"),
                        "handler": json_data.get("handler"),
                        "session_purpose": json_data.get("session_purpose"),
                        "field_support": json_data.get("field_support"),
                        "dog_name": json_data.get("dog_name"),
                        "location": json_data.get("location"),
                        "search_area_size": json_data.get("search_area_size"),
                        "num_subjects": json_data.get("num_subjects"),
                        "handler_knowledge": json_data.get("handler_knowledge"),
                        "weather": json_data.get("weather"),
                        "temperature": json_data.get("temperature"),
                        "wind_direction": json_data.get("wind_direction"),
                        "wind_speed": json_data.get("wind_speed"),
                        "search_type": json_data.get("search_type"),
                        "drive_level": json_data.get("drive_level"),
                        "subjects_found": json_data.get("subjects_found"),
                        "comments": json_data.get("comments"),
                        "image_files": image_files_json,
                        "entry_type": json_data.get("entry_type"),
                        "update_time": json_data.get("update_time"),
                        "uuid": json_data.get("uuid"),
                        "user_name": json_data.get("user_name", get_username()),
                        "status": json_data.get("status", "active")
                    }
                )
            
            conn.commit()
            print(f"Sync: Inserted/updated airscenting session {json_data.get('session_number')} for {json_data.get('dog_name')}")
        
        # Restore original DB type
        if old_db_type != db_type:
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
        
        return True
        
    except Exception as e:
        print(f"Error inserting airscenting session from JSON: {e}")
        import traceback
        traceback.print_exc()
        return False


def insert_trailing_session_from_json(json_data, db_type):
    """Insert a new trailing session into database from JSON data."""
    try:
        import config
        from sqlalchemy import text
        from ui_utils import get_username
        
        old_db_type = config.DB_TYPE
        config.DB_TYPE = db_type
        
        from database import engine, get_connection
        from importlib import reload
        import database
        
        if old_db_type != db_type:
            engine.dispose()
            reload(database)
        
        with database.get_connection() as conn:
            map_files = json_data.get("t_map_files", [])
            if isinstance(map_files, list):
                map_files_json = json.dumps(map_files)
            else:
                map_files_json = map_files or ""
            
            # Check if session already exists (by t_session_number + t_dog_name)
            check_result = conn.execute(
                text("""
                    SELECT id FROM t_training_sessions 
                    WHERE t_session_number = :session_number AND t_dog_name = :dog_name
                """),
                {
                    "session_number": json_data.get("t_session_number"),
                    "dog_name": json_data.get("t_dog_name")
                }
            )
            existing = check_result.fetchone()
            
            if existing:
                # Session exists - update it
                print(f"Sync: Trailing session {json_data.get('t_session_number')}/{json_data.get('t_dog_name')} exists, updating...")
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
                            uuid = :uuid
                        WHERE t_session_number = :t_session_number AND t_dog_name = :t_dog_name
                    """),
                    {
                        "t_date": json_data.get("t_date"),
                        "t_handler": json_data.get("t_handler"),
                        "t_field_support": json_data.get("t_field_support"),
                        "t_location": json_data.get("t_location"),
                        "t_start_time": json_data.get("t_start_time"),
                        "t_finish_time": json_data.get("t_finish_time"),
                        "t_trail_age": json_data.get("t_trail_age"),
                        "t_trail_length": json_data.get("t_trail_length"),
                        "t_difficulty": json_data.get("t_difficulty"),
                        "t_trail_layer": json_data.get("t_trail_layer"),
                        "t_cross_track_layer": json_data.get("t_cross_track_layer"),
                        "t_cross_track_age": json_data.get("t_cross_track_age"),
                        "t_weather_laying": json_data.get("t_weather_laying"),
                        "t_temperature_laying": json_data.get("t_temperature_laying"),
                        "t_wind_speed_laying": json_data.get("t_wind_speed_laying"),
                        "t_wind_direction_laying": json_data.get("t_wind_direction_laying"),
                        "t_humidity_laying": json_data.get("t_humidity_laying"),
                        "t_weather_running": json_data.get("t_weather_running"),
                        "t_temperature_running": json_data.get("t_temperature_running"),
                        "t_wind_speed_running": json_data.get("t_wind_speed_running"),
                        "t_wind_direction_running": json_data.get("t_wind_direction_running"),
                        "t_humidity_running": json_data.get("t_humidity_running"),
                        "t_start_behavior": json_data.get("t_start_behavior"),
                        "t_consistency": json_data.get("t_consistency"),
                        "t_head_position": json_data.get("t_head_position"),
                        "t_pace": json_data.get("t_pace"),
                        "t_indication": json_data.get("t_indication"),
                        "t_time_to_complete": json_data.get("t_time_to_complete"),
                        "t_success_rate": json_data.get("t_success_rate"),
                        "t_impression": json_data.get("t_impression"),
                        "t_map_files": map_files_json,
                        "update_time": json_data.get("update_time"),
                        "uuid": json_data.get("uuid"),
                        "t_session_number": json_data.get("t_session_number"),
                        "t_dog_name": json_data.get("t_dog_name")
                    }
                )
            else:
                # Insert new session
                conn.execute(
                    text("""
                        INSERT INTO t_training_sessions 
                        (t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                         t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                         t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                         t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                         t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                         t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                         t_time_to_complete, t_success_rate, t_impression, t_map_files,
                         update_time, uuid, user_name, status)
                        VALUES (:t_session_number, :t_dog_name, :t_date, :t_handler, :t_field_support,
                                :t_location, :t_start_time, :t_finish_time, :t_trail_age, :t_trail_length,
                                :t_difficulty, :t_trail_layer, :t_cross_track_layer, :t_cross_track_age,
                                :t_weather_laying, :t_temperature_laying, :t_wind_speed_laying, :t_wind_direction_laying, :t_humidity_laying,
                                :t_weather_running, :t_temperature_running, :t_wind_speed_running, :t_wind_direction_running, :t_humidity_running,
                                :t_start_behavior, :t_consistency, :t_head_position, :t_pace, :t_indication,
                                :t_time_to_complete, :t_success_rate, :t_impression, :t_map_files,
                                :update_time, :uuid, :user_name, :status)
                    """),
                    {
                        "t_session_number": json_data.get("t_session_number"),
                        "t_dog_name": json_data.get("t_dog_name"),
                        "t_date": json_data.get("t_date"),
                        "t_handler": json_data.get("t_handler"),
                        "t_field_support": json_data.get("t_field_support"),
                        "t_location": json_data.get("t_location"),
                        "t_start_time": json_data.get("t_start_time"),
                        "t_finish_time": json_data.get("t_finish_time"),
                        "t_trail_age": json_data.get("t_trail_age"),
                        "t_trail_length": json_data.get("t_trail_length"),
                        "t_difficulty": json_data.get("t_difficulty"),
                        "t_trail_layer": json_data.get("t_trail_layer"),
                        "t_cross_track_layer": json_data.get("t_cross_track_layer"),
                        "t_cross_track_age": json_data.get("t_cross_track_age"),
                        "t_weather_laying": json_data.get("t_weather_laying"),
                        "t_temperature_laying": json_data.get("t_temperature_laying"),
                        "t_wind_speed_laying": json_data.get("t_wind_speed_laying"),
                        "t_wind_direction_laying": json_data.get("t_wind_direction_laying"),
                        "t_humidity_laying": json_data.get("t_humidity_laying"),
                        "t_weather_running": json_data.get("t_weather_running"),
                        "t_temperature_running": json_data.get("t_temperature_running"),
                        "t_wind_speed_running": json_data.get("t_wind_speed_running"),
                        "t_wind_direction_running": json_data.get("t_wind_direction_running"),
                        "t_humidity_running": json_data.get("t_humidity_running"),
                        "t_start_behavior": json_data.get("t_start_behavior"),
                        "t_consistency": json_data.get("t_consistency"),
                        "t_head_position": json_data.get("t_head_position"),
                        "t_pace": json_data.get("t_pace"),
                        "t_indication": json_data.get("t_indication"),
                        "t_time_to_complete": json_data.get("t_time_to_complete"),
                        "t_success_rate": json_data.get("t_success_rate"),
                        "t_impression": json_data.get("t_impression"),
                        "t_map_files": map_files_json,
                        "update_time": json_data.get("update_time"),
                        "uuid": json_data.get("uuid"),
                        "user_name": json_data.get("user_name", get_username()),
                        "status": json_data.get("status", "active")
                    }
                )
            
            conn.commit()
            print(f"Sync: Inserted/updated trailing session {json_data.get('t_session_number')} for {json_data.get('t_dog_name')}")
        
        # Restore original DB type
        if old_db_type != db_type:
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
        
        return True
        
    except Exception as e:
        print(f"Error inserting trailing session from JSON: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_db_from_json(json_data, db_type):
    """Update database record from JSON data.
    
    Automatically detects whether it's an airscenting or trailing session
    based on the presence of 't_session_number' key.
    """
    # Detect session type
    is_trailing = 't_session_number' in json_data
    
    if is_trailing:
        return update_trailing_db_from_json(json_data, db_type)
    else:
        return update_airscenting_db_from_json(json_data, db_type)


def update_airscenting_db_from_json(json_data, db_type):
    """Update airscenting database record from JSON data."""
    try:
        import config
        from sqlalchemy import text
        from ui_utils import get_username
        
        old_db_type = config.DB_TYPE
        config.DB_TYPE = db_type
        
        from database import engine, get_connection
        from importlib import reload
        import database
        
        if old_db_type != db_type:
            engine.dispose()
            reload(database)
        
        with database.get_connection() as conn:
            # Update main session
            image_files = json_data.get("image_files", [])
            if isinstance(image_files, list):
                image_files_json = json.dumps(image_files)
            else:
                image_files_json = image_files or ""
            
            conn.execute(
                text("""
                    UPDATE training_sessions SET
                        date = :date,
                        handler = :handler,
                        session_purpose = :session_purpose,
                        field_support = :field_support,
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
                        update_time = :update_time,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE uuid = :uuid
                """),
                {
                    "date": json_data.get("date"),
                    "handler": json_data.get("handler"),
                    "session_purpose": json_data.get("session_purpose"),
                    "field_support": json_data.get("field_support"),
                    "location": json_data.get("location"),
                    "search_area_size": json_data.get("search_area_size"),
                    "num_subjects": json_data.get("num_subjects"),
                    "handler_knowledge": json_data.get("handler_knowledge"),
                    "weather": json_data.get("weather"),
                    "temperature": json_data.get("temperature"),
                    "wind_direction": json_data.get("wind_direction"),
                    "wind_speed": json_data.get("wind_speed"),
                    "search_type": json_data.get("search_type"),
                    "drive_level": json_data.get("drive_level"),
                    "subjects_found": json_data.get("subjects_found"),
                    "comments": json_data.get("comments"),
                    "image_files": image_files_json,
                    "update_time": json_data.get("update_time"),
                    "uuid": json_data.get("uuid")
                }
            )
            conn.commit()
        
        # Restore original DB type
        if old_db_type != db_type:
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
        
        return True
        
    except Exception as e:
        print(f"Error updating airscenting DB from JSON: {e}")
        return False


def update_trailing_db_from_json(json_data, db_type):
    """Update trailing database record from JSON data."""
    try:
        import config
        from sqlalchemy import text
        
        old_db_type = config.DB_TYPE
        config.DB_TYPE = db_type
        
        from database import engine, get_connection
        from importlib import reload
        import database
        
        if old_db_type != db_type:
            engine.dispose()
            reload(database)
        
        with database.get_connection() as conn:
            # Handle map files
            map_files = json_data.get("t_map_files", [])
            if isinstance(map_files, list):
                map_files_json = json.dumps(map_files)
            else:
                map_files_json = map_files or ""
            
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
                        update_time = :update_time
                    WHERE uuid = :uuid
                """),
                {
                    "t_date": json_data.get("t_date"),
                    "t_handler": json_data.get("t_handler"),
                    "t_field_support": json_data.get("t_field_support"),
                    "t_location": json_data.get("t_location"),
                    "t_start_time": json_data.get("t_start_time"),
                    "t_finish_time": json_data.get("t_finish_time"),
                    "t_trail_age": json_data.get("t_trail_age"),
                    "t_trail_length": json_data.get("t_trail_length"),
                    "t_difficulty": json_data.get("t_difficulty"),
                    "t_trail_layer": json_data.get("t_trail_layer"),
                    "t_cross_track_layer": json_data.get("t_cross_track_layer"),
                    "t_cross_track_age": json_data.get("t_cross_track_age"),
                    "t_weather_laying": json_data.get("t_weather_laying"),
                    "t_temperature_laying": json_data.get("t_temperature_laying"),
                    "t_wind_speed_laying": json_data.get("t_wind_speed_laying"),
                    "t_wind_direction_laying": json_data.get("t_wind_direction_laying"),
                    "t_humidity_laying": json_data.get("t_humidity_laying"),
                    "t_weather_running": json_data.get("t_weather_running"),
                    "t_temperature_running": json_data.get("t_temperature_running"),
                    "t_wind_speed_running": json_data.get("t_wind_speed_running"),
                    "t_wind_direction_running": json_data.get("t_wind_direction_running"),
                    "t_humidity_running": json_data.get("t_humidity_running"),
                    "t_start_behavior": json_data.get("t_start_behavior"),
                    "t_consistency": json_data.get("t_consistency"),
                    "t_head_position": json_data.get("t_head_position"),
                    "t_pace": json_data.get("t_pace"),
                    "t_indication": json_data.get("t_indication"),
                    "t_time_to_complete": json_data.get("t_time_to_complete"),
                    "t_success_rate": json_data.get("t_success_rate"),
                    "t_impression": json_data.get("t_impression"),
                    "t_map_files": map_files_json,
                    "update_time": json_data.get("update_time"),
                    "uuid": json_data.get("uuid")
                }
            )
            conn.commit()
            print(f"Sync: Updated trailing session {json_data.get('t_session_number')} from JSON")
        
        # Restore original DB type
        if old_db_type != db_type:
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
        
        return True
        
    except Exception as e:
        print(f"Error updating trailing DB from JSON: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_json_file(filepath):
    """Validate that a JSON file can be loaded without errors.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except Exception as e:
        print(f"JSON validation failed for {filepath}: {e}")
        return False


def sync_primary_to_secondary(primary_dict, secondary_dict, secondary_folder):
    """
    Sync primary JSON folder to secondary - copy newer/missing files.
    Only copies valid JSON files.
    Uses file modification time for comparison (handles manual edits).
    
    Returns:
        int: Number of files copied
    """
    count = 0
    
    for key, primary_info in primary_dict.items():
        secondary_info = secondary_dict.get(key)
        
        should_copy = False
        
        if not secondary_info:
            # File not in secondary
            should_copy = True
        else:
            # Use file modification time for comparison (more reliable for manual edits)
            primary_mtime = primary_info.get("file_mtime") or primary_info.get("update_time")
            secondary_mtime = secondary_info.get("file_mtime") or secondary_info.get("update_time")
            
            if primary_mtime and secondary_mtime:
                if primary_mtime > secondary_mtime:
                    should_copy = True
        
        if should_copy:
            try:
                src = primary_info["filepath"]
                
                # Validate JSON before copying
                if not validate_json_file(src):
                    print(f"Sync: Skipping invalid JSON file: {src.name}")
                    continue
                
                dst = Path(secondary_folder) / src.name
                shutil.copy2(str(src), str(dst))
                count += 1
                print(f"Sync: Copied to secondary: {dst.name}")
            except Exception as e:
                print(f"Sync error copying to secondary: {e}")
    
    return count


def sync_secondary_to_primary(secondary_dict, primary_dict, primary_folder, db_type):
    """
    Sync secondary JSON folder to primary - copy newer files and update DB.
    Only copies valid JSON files.
    Uses file modification time for comparison (handles manual edits).
    
    Returns:
        int: Number of files copied
    """
    count = 0
    
    for key, secondary_info in secondary_dict.items():
        primary_info = primary_dict.get(key)
        
        should_copy = False
        
        if not primary_info:
            # File not in primary
            should_copy = True
        else:
            # Use file modification time for comparison (more reliable for manual edits)
            secondary_mtime = secondary_info.get("file_mtime") or secondary_info.get("update_time")
            primary_mtime = primary_info.get("file_mtime") or primary_info.get("update_time")
            
            if secondary_mtime and primary_mtime:
                if secondary_mtime > primary_mtime:
                    should_copy = True
        
        if should_copy:
            try:
                src = secondary_info["filepath"]
                
                # Validate JSON before copying
                if not validate_json_file(src):
                    print(f"Sync: Skipping invalid JSON file from secondary: {src.name}")
                    continue
                
                dst = Path(primary_folder) / src.name
                shutil.copy2(str(src), str(dst))
                count += 1
                print(f"Sync: Copied from secondary to primary: {dst.name}")
                
                # Also update DB if this file has a UUID
                if secondary_info.get("has_uuid"):
                    update_db_from_json(secondary_info["data"], db_type)
                    
            except Exception as e:
                print(f"Sync error copying from secondary: {e}")
    
    return count


# Global sync manager instance
_sync_manager = None

def get_sync_manager():
    """Get the global sync manager instance."""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = BackupSyncManager()
    return _sync_manager
