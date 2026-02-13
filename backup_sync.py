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
Backup Sync System for Training Logger

This module handles synchronization between:
- SQLite/PostgreSQL database
- Primary JSON backup folder
- Secondary JSON backup folder (potentially shared on network)

Key features:
- SHA-256 checksums to detect changes
- File timestamps to track modifications
- Consistent file naming: a_{dog}_{session}.json (airscenting), t_{dog}_{session}.json (trailing)
- Multi-user support via shared secondary backup
- Database rebuild from backups if corrupted
"""

import json
import hashlib
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def compute_checksum(data: dict) -> str:
    """
    Compute SHA-256 checksum of JSON data.
    Sorts keys for consistent output regardless of dict ordering.
    
    Args:
        data: Dictionary to compute checksum for
        
    Returns:
        Hex string of SHA-256 checksum
    """
    # Sort keys and convert to JSON string for consistent hashing
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


# Fields that legitimately differ between DB and JSON representations
# of the same session and must be excluded from content comparison.
_METADATA_FIELDS = {
    'id',                   # DB auto-increment, absent from JSON
    'checksum',             # Stored checksum, not content
    'primary_timestamp',    # Sync bookkeeping
    'secondary_timestamp',  # Sync bookkeeping
}


def compute_content_checksum(data: dict) -> str:
    """
    Compute checksum of session CONTENT only, ignoring metadata fields
    that legitimately differ between DB and JSON representations.
    
    Also normalizes:
    - update_time format: DB's "2025-01-15 10:30:00" vs JSON's "2025-01-15T10:30:00"
    - image_files / t_map_files: DB stores as JSON string, JSON stores as array
    - None vs '' differences
    
    Use this for DB-vs-JSON comparison. Use compute_checksum() for
    same-source comparisons.
    """
    # Copy and strip metadata
    clean = {k: v for k, v in data.items() if k not in _METADATA_FIELDS}
    
    # Normalize update_time: both "2025-01-15 10:30:00" and
    # "2025-01-15T10:30:00" should hash the same
    ut = clean.get('update_time')
    if ut and isinstance(ut, str):
        clean['update_time'] = ut.replace('T', ' ').rstrip('Z').split('+')[0].strip()
    
    # Normalize image_files and t_map_files: DB stores lists as JSON strings,
    # JSON files store them as actual arrays
    for list_field in ('image_files', 't_map_files'):
        val = clean.get(list_field)
        if isinstance(val, str) and val.startswith('['):
            try:
                clean[list_field] = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                pass
    
    # Normalize None / empty-string differences, then remove empty values.
    # This ensures old JSON files (missing newer fields) match DB sessions
    # where those fields exist but are empty.
    for k, v in list(clean.items()):
        if v is None:
            clean[k] = ''
    
    # Remove keys with empty values (empty string or empty list).
    # A field that is '' in DB but absent from JSON is semantically identical.
    for k, v in list(clean.items()):
        if v == '' or (isinstance(v, list) and len(v) == 0):
            del clean[k]
    
    # Normalize list ordering for child table data so that
    # DB sort order and JSON save order produce the same checksum
    for str_list_field in ('selected_terrains', 'selected_purposes',
                           't_selected_terrains', 't_selected_purposes'):
        val = clean.get(str_list_field)
        if isinstance(val, list):
            clean[str_list_field] = sorted(val)
    
    # Sort subject_responses by subject_number
    responses = clean.get('subject_responses')
    if isinstance(responses, list) and responses:
        clean['subject_responses'] = sorted(
            responses,
            key=lambda r: r.get('subject_number', 0) if isinstance(r, dict) else 0
        )
    
    # Sort t_distractions by type name for consistent ordering
    distractions = clean.get('t_distractions')
    if isinstance(distractions, list) and distractions:
        clean['t_distractions'] = sorted(
            distractions,
            key=lambda d: json.dumps(d, sort_keys=True) if isinstance(d, dict) else str(d)
        )
    
    json_str = json.dumps(clean, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def get_file_mtime(filepath: Path) -> Optional[datetime]:
    """Get file modification time as datetime."""
    try:
        return datetime.fromtimestamp(filepath.stat().st_mtime)
    except:
        return None


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use in a filename."""
    return re.sub(r'[^\w\-]', '_', name)


def generate_json_filename(session_type: str, user_name: str, dog_name: str, session_number: int) -> str:
    """
    Generate consistent JSON filename.
    
    Args:
        session_type: 'a' for airscenting, 't' for trailing
        user_name: Username from database
        dog_name: Name of the dog
        session_number: Session number from database
        
    Returns:
        Filename like 'a_john_Fido_1.json' or 't_mary_Rex_5.json'
    """
    safe_user = sanitize_filename(user_name) if user_name else 'unknown'
    safe_dog = sanitize_filename(dog_name)
    return f"{session_type}_{safe_user}_{safe_dog}_{session_number}.json"


def parse_json_filename(filename: str) -> Optional[Tuple[str, str, str, int]]:
    """
    Parse a JSON filename to extract session info.
    
    Args:
        filename: Filename like 'a_john_Fido_1.json' or 't_mary_Rex_5.json'
        
    Returns:
        Tuple of (session_type, user_name, dog_name, session_number) or None if invalid
    """
    # Match new pattern: {type}_{user}_{dog}_{number}.json
    match = re.match(r'^([at])_([^_]+)_(.+)_(\d+)\.json$', filename)
    if match:
        return match.group(1), match.group(2), match.group(3), int(match.group(4))
    
    # Match old pattern without user: {type}_{dog}_{number}.json
    match = re.match(r'^([at])_(.+)_(\d+)\.json$', filename)
    if match:
        return match.group(1), None, match.group(2), int(match.group(3))
    
    # Try legacy pattern: {dog}_session_{number}_{date}.json
    match = re.match(r'^(.+)_session_(\d+)_\d+\.json$', filename)
    if match:
        return None, None, match.group(1), int(match.group(2))
    
    return None


def validate_json_file(filepath: Path) -> Tuple[bool, Optional[dict]]:
    """
    Validate a JSON file can be loaded.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Tuple of (is_valid, data or None)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, data
    except Exception as e:
        # print(f"Invalid JSON file {filepath}: {e}")
        return False, None


def is_trailing_session(data: dict) -> bool:
    """Check if session data is for trailing (vs airscenting)."""
    return 't_session_number' in data


# ==============================================================================
# SESSION DATA STRUCTURES
# ==============================================================================

class SessionInfo:
    """Information about a session from any source."""
    
    def __init__(self, 
                 session_type: str,  # 'a' or 't'
                 dog_name: str,
                 session_number: int,
                 uuid: Optional[str] = None,
                 checksum: Optional[str] = None,
                 update_time: Optional[datetime] = None,
                 data: Optional[dict] = None,
                 source: str = 'unknown',  # 'db', 'primary', 'secondary'
                 file_mtime: Optional[datetime] = None,
                 filepath: Optional[Path] = None,
                 user_name: Optional[str] = None):
        self.session_type = session_type
        self.dog_name = dog_name
        self.session_number = session_number
        self.uuid = uuid
        self.checksum = checksum
        self.update_time = update_time
        self.data = data
        self.source = source
        self.file_mtime = file_mtime
        self.filepath = filepath
        self.user_name = user_name or (data.get('user_name') if data else None)
    
    @property
    def key(self) -> str:
        """Unique key for this session."""
        return f"{self.session_type}_{self.dog_name}_{self.session_number}"
    
    @property
    def filename(self) -> str:
        """Generate filename for this session."""
        return generate_json_filename(self.session_type, self.user_name, self.dog_name, self.session_number)
    
    def __repr__(self):
        return f"SessionInfo({self.key}, source={self.source}, checksum={self.checksum[:8] if self.checksum else 'None'}...)"


# ==============================================================================
# DATABASE OPERATIONS
# ==============================================================================

class DatabaseOps:
    """Database operations for backup sync."""
    
    def __init__(self, db_type: str):
        self.db_type = db_type
    
    def _get_connection(self):
        """Get database connection with correct type."""
        import config
        from database import engine, get_connection
        from importlib import reload
        import database
        
        old_db_type = config.DB_TYPE
        if old_db_type != self.db_type:
            config.DB_TYPE = self.db_type
            engine.dispose()
            reload(database)
        
        return database.get_connection()
    
    def is_db_healthy(self) -> bool:
        """Check if database is accessible and has required tables."""
        try:
            from sqlalchemy import text
            with self._get_connection() as conn:
                # Try to query both session tables
                conn.execute(text("SELECT COUNT(*) FROM training_sessions"))
                conn.execute(text("SELECT COUNT(*) FROM t_training_sessions"))
            return True
        except Exception as e:
            # print(f"Database health check failed: {e}")
            return False
    
    def get_all_sessions(self) -> List[SessionInfo]:
        """Get all sessions from database."""
        sessions = []
        sessions.extend(self._get_airscenting_sessions())
        sessions.extend(self._get_trailing_sessions())
        return sessions
    
    def _get_airscenting_sessions(self) -> List[SessionInfo]:
        """Get all airscenting sessions from database, including child table data."""
        sessions = []
        try:
            from sqlalchemy import text
            with self._get_connection() as conn:
                result = conn.execute(text("""
                    SELECT id, session_number, dog_name, date, handler, session_purpose,
                           field_support, location, search_area_size, num_subjects,
                           handler_knowledge, weather, temperature, wind_direction,
                           wind_speed, search_type, drive_level, subjects_found,
                           comments, image_files, entry_type, update_time, uuid,
                           status, checksum, primary_timestamp, secondary_timestamp, user_name,
                           a_percent_searched, start_time, finish_time
                    FROM training_sessions
                """))
                # Fetch ALL rows immediately before any other queries —
                # prevents cursor invalidation on some DB backends.
                rows = result.fetchall()
                
                # Batch-load all child table data for efficiency
                terrain_result = conn.execute(text(
                    "SELECT session_id, terrain_name FROM selected_terrains ORDER BY session_id, terrain_name"
                ))
                terrains_by_id = {}
                for r in terrain_result.fetchall():
                    terrains_by_id.setdefault(r[0], []).append(r[1])
                
                response_result = conn.execute(text(
                    "SELECT session_id, subject_number, tfr, refind "
                    "FROM subject_responses ORDER BY session_id, subject_number"
                ))
                responses_by_id = {}
                for r in response_result.fetchall():
                    responses_by_id.setdefault(r[0], []).append({
                        'subject_number': r[1],
                        'tfr': r[2] or '',
                        'refind': r[3] or ''
                    })
                
                purpose_result = conn.execute(text(
                    "SELECT session_id, purpose_name FROM a_selected_purposes ORDER BY session_id, purpose_name"
                ))
                purposes_by_id = {}
                for r in purpose_result.fetchall():
                    purposes_by_id.setdefault(r[0], []).append(r[1])
                
                for row in rows:
                    session_id = row[0]
                    user_name = row[27] or ''  # user_name column
                    data = {
                        'id': row[0],
                        'session_number': row[1],
                        'dog_name': row[2],
                        'date': str(row[3]) if row[3] else '',
                        'handler': row[4] or '',
                        'session_purpose': row[5] or '',
                        'field_support': row[6] or '',
                        'location': row[7] or '',
                        'search_area_size': row[8] or '',
                        'num_subjects': row[9] or '',
                        'handler_knowledge': row[10] or '',
                        'weather': row[11] or '',
                        'temperature': row[12] or '',
                        'wind_direction': row[13] or '',
                        'wind_speed': row[14] or '',
                        'search_type': row[15] or '',
                        'drive_level': row[16] or '',
                        'subjects_found': row[17] or '',
                        'comments': row[18] or '',
                        'image_files': row[19] or '',
                        'entry_type': row[20] or 'Airscent',
                        'update_time': str(row[21]) if row[21] else '',
                        'uuid': row[22] or '',
                        'status': row[23] or 'active',
                        'user_name': user_name,
                        'a_percent_searched': row[28] or '',
                        'start_time': row[29] or '',
                        'finish_time': row[30] or '',
                        # Child table data
                        'selected_terrains': terrains_by_id.get(session_id, []),
                        'subject_responses': responses_by_id.get(session_id, []),
                        'selected_purposes': purposes_by_id.get(session_id, []),
                    }
                    
                    # Parse update_time
                    update_time = None
                    if row[21]:
                        try:
                            if isinstance(row[21], datetime):
                                update_time = row[21]
                            else:
                                update_time = datetime.fromisoformat(str(row[21]).replace('Z', '+00:00'))
                        except:
                            pass
                    
                    sessions.append(SessionInfo(
                        session_type='a',
                        dog_name=row[2] or 'unknown',
                        session_number=row[1],
                        uuid=row[22],
                        checksum=row[24],  # checksum column
                        update_time=update_time,
                        data=data,
                        source='db',
                        user_name=user_name
                    ))
        except Exception as e:
            # print(f"Error getting airscenting sessions: {e}")
            pass
        
        return sessions
    
    def _get_trailing_sessions(self) -> List[SessionInfo]:
        """Get all trailing sessions from database, including child table data."""
        sessions = []
        try:
            from sqlalchemy import text
            with self._get_connection() as conn:
                result = conn.execute(text("""
                    SELECT id, t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                           t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                           t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                           t_weather_laying, t_temperature_laying, t_wind_speed_laying, 
                           t_wind_direction_laying, t_humidity_laying,
                           t_weather_running, t_temperature_running, t_wind_speed_running,
                           t_wind_direction_running, t_humidity_running,
                           t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                           t_time_to_complete, t_success_rate, t_impression, t_map_files,
                           update_time, uuid, status, checksum, primary_timestamp, secondary_timestamp, user_name
                    FROM t_training_sessions
                """))
                # Fetch ALL rows immediately before any other queries —
                # prevents cursor invalidation on some DB backends.
                rows = result.fetchall()
                
                # Batch-load all child table data for efficiency
                terrain_result = conn.execute(text(
                    "SELECT t_session_id, terrain_name FROM t_selected_terrains ORDER BY t_session_id, terrain_name"
                ))
                terrains_by_id = {}
                for r in terrain_result.fetchall():
                    terrains_by_id.setdefault(r[0], []).append(r[1])
                
                purpose_result = conn.execute(text(
                    "SELECT t_session_id, purpose_name FROM t_selected_purposes ORDER BY t_session_id, purpose_name"
                ))
                purposes_by_id = {}
                for r in purpose_result.fetchall():
                    purposes_by_id.setdefault(r[0], []).append(r[1])
                
                distraction_result = conn.execute(text(
                    "SELECT t_session_id, distraction_data FROM t_distractions ORDER BY t_session_id"
                ))
                distractions_by_id = {}
                for r in distraction_result.fetchall():
                    try:
                        distractions_by_id.setdefault(r[0], []).append(json.loads(r[1]))
                    except (json.JSONDecodeError, TypeError):
                        distractions_by_id.setdefault(r[0], []).append(r[1])
                
                for row in rows:
                    session_id = row[0]
                    user_name = row[40] or ''  # user_name column
                    data = {
                        'id': row[0],
                        't_session_number': row[1],
                        't_dog_name': row[2],
                        't_date': str(row[3]) if row[3] else '',
                        't_handler': row[4] or '',
                        't_field_support': row[5] or '',
                        't_location': row[6] or '',
                        't_start_time': row[7] or '',
                        't_finish_time': row[8] or '',
                        't_trail_age': row[9] or '',
                        't_trail_length': row[10] or '',
                        't_difficulty': row[11] or '',
                        't_trail_layer': row[12] or '',
                        't_cross_track_layer': row[13] or '',
                        't_cross_track_age': row[14] or '',
                        't_weather_laying': row[15] or '',
                        't_temperature_laying': row[16] or '',
                        't_wind_speed_laying': row[17] or '',
                        't_wind_direction_laying': row[18] or '',
                        't_humidity_laying': row[19] or '',
                        't_weather_running': row[20] or '',
                        't_temperature_running': row[21] or '',
                        't_wind_speed_running': row[22] or '',
                        't_wind_direction_running': row[23] or '',
                        't_humidity_running': row[24] or '',
                        't_start_behavior': row[25] or '',
                        't_consistency': row[26] or '',
                        't_head_position': row[27] or '',
                        't_pace': row[28] or '',
                        't_indication': row[29] or '',
                        't_time_to_complete': row[30] or '',
                        't_success_rate': row[31] or '',
                        't_impression': row[32] or '',
                        't_map_files': row[33] or '',
                        'update_time': str(row[34]) if row[34] else '',
                        'uuid': row[35] or '',
                        'status': row[36] or 'active',
                        'user_name': user_name,
                        # Child table data
                        't_selected_terrains': terrains_by_id.get(session_id, []),
                        't_selected_purposes': purposes_by_id.get(session_id, []),
                        't_distractions': distractions_by_id.get(session_id, []),
                    }
                    
                    # Parse update_time
                    update_time = None
                    if row[34]:
                        try:
                            if isinstance(row[34], datetime):
                                update_time = row[34]
                            else:
                                update_time = datetime.fromisoformat(str(row[34]).replace('Z', '+00:00'))
                        except:
                            pass
                    
                    sessions.append(SessionInfo(
                        session_type='t',
                        dog_name=row[2] or 'unknown',
                        session_number=row[1],
                        uuid=row[35],
                        checksum=row[37],  # checksum column
                        update_time=update_time,
                        data=data,
                        source='db',
                        user_name=user_name
                    ))
        except Exception as e:
            # print(f"Error getting trailing sessions: {e}")
            pass
        
        return sessions
    
    def upsert_session(self, session: SessionInfo, primary_ts: Optional[datetime], 
                       secondary_ts: Optional[datetime]) -> bool:
        """Insert or update a session in the database."""
        if session.session_type == 'a':
            return self._upsert_airscenting_session(session, primary_ts, secondary_ts)
        else:
            return self._upsert_trailing_session(session, primary_ts, secondary_ts)
    
    def _upsert_airscenting_session(self, session: SessionInfo, primary_ts: Optional[datetime],
                                     secondary_ts: Optional[datetime]) -> bool:
        """Insert or update an airscenting session, including child table data."""
        try:
            from sqlalchemy import text
            data = session.data
            
            # Ensure session_number is int (JSON might store as string)
            try:
                sn = int(session.session_number)
            except (ValueError, TypeError):
                print(f"Invalid session_number: {session.session_number}")
                return False
            
            with self._get_connection() as conn:
                # Check if exists
                result = conn.execute(text("""
                    SELECT id FROM training_sessions 
                    WHERE session_number = :session_number AND dog_name = :dog_name
                """), {
                    'session_number': sn,
                    'dog_name': session.dog_name
                })
                existing = result.fetchone()
                
                # Prepare image_files as JSON string
                image_files = data.get('image_files', '')
                if isinstance(image_files, list):
                    image_files = json.dumps(image_files)
                
                if existing:
                    session_id = existing[0]
                    # Update
                    conn.execute(text("""
                        UPDATE training_sessions SET
                            date = :date, handler = :handler, session_purpose = :session_purpose,
                            field_support = :field_support, location = :location,
                            search_area_size = :search_area_size, num_subjects = :num_subjects,
                            handler_knowledge = :handler_knowledge, weather = :weather,
                            temperature = :temperature, wind_direction = :wind_direction,
                            wind_speed = :wind_speed, search_type = :search_type,
                            drive_level = :drive_level, subjects_found = :subjects_found,
                            a_percent_searched = :a_percent_searched,
                            start_time = :start_time, finish_time = :finish_time,
                            comments = :comments, image_files = :image_files,
                            entry_type = :entry_type, update_time = :update_time,
                            uuid = :uuid, status = :status, checksum = :checksum,
                            primary_timestamp = :primary_timestamp,
                            secondary_timestamp = :secondary_timestamp,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE session_number = :session_number AND dog_name = :dog_name
                    """), {
                        'date': data.get('date'),
                        'handler': data.get('handler'),
                        'session_purpose': data.get('session_purpose'),
                        'field_support': data.get('field_support'),
                        'location': data.get('location'),
                        'search_area_size': data.get('search_area_size'),
                        'num_subjects': data.get('num_subjects'),
                        'handler_knowledge': data.get('handler_knowledge'),
                        'weather': data.get('weather'),
                        'temperature': data.get('temperature'),
                        'wind_direction': data.get('wind_direction'),
                        'wind_speed': data.get('wind_speed'),
                        'search_type': data.get('search_type'),
                        'drive_level': data.get('drive_level'),
                        'subjects_found': data.get('subjects_found'),
                        'a_percent_searched': data.get('a_percent_searched'),
                        'start_time': data.get('start_time'),
                        'finish_time': data.get('finish_time'),
                        'comments': data.get('comments'),
                        'image_files': image_files,
                        'entry_type': data.get('entry_type', 'Airscent'),
                        'update_time': session.update_time,
                        'uuid': session.uuid,
                        'status': data.get('status', 'active'),
                        'checksum': session.checksum,
                        'primary_timestamp': primary_ts,
                        'secondary_timestamp': secondary_ts,
                        'session_number': sn,
                        'dog_name': session.dog_name
                    })
                else:
                    # Insert
                    from ui_utils import get_username
                    conn.execute(text("""
                        INSERT INTO training_sessions 
                        (date, session_number, handler, session_purpose, field_support,
                         dog_name, location, search_area_size, num_subjects, handler_knowledge,
                         weather, temperature, wind_direction, wind_speed, search_type,
                         drive_level, subjects_found, a_percent_searched, start_time, finish_time,
                         comments, image_files, entry_type,
                         update_time, uuid, status, checksum, primary_timestamp, 
                         secondary_timestamp, user_name)
                        VALUES (:date, :session_number, :handler, :session_purpose, :field_support,
                                :dog_name, :location, :search_area_size, :num_subjects, :handler_knowledge,
                                :weather, :temperature, :wind_direction, :wind_speed, :search_type,
                                :drive_level, :subjects_found, :a_percent_searched, :start_time, :finish_time,
                                :comments, :image_files, :entry_type,
                                :update_time, :uuid, :status, :checksum, :primary_timestamp,
                                :secondary_timestamp, :user_name)
                    """), {
                        'date': data.get('date'),
                        'session_number': sn,
                        'handler': data.get('handler'),
                        'session_purpose': data.get('session_purpose'),
                        'field_support': data.get('field_support'),
                        'dog_name': session.dog_name,
                        'location': data.get('location'),
                        'search_area_size': data.get('search_area_size'),
                        'num_subjects': data.get('num_subjects'),
                        'handler_knowledge': data.get('handler_knowledge'),
                        'weather': data.get('weather'),
                        'temperature': data.get('temperature'),
                        'wind_direction': data.get('wind_direction'),
                        'wind_speed': data.get('wind_speed'),
                        'search_type': data.get('search_type'),
                        'drive_level': data.get('drive_level'),
                        'subjects_found': data.get('subjects_found'),
                        'a_percent_searched': data.get('a_percent_searched'),
                        'start_time': data.get('start_time'),
                        'finish_time': data.get('finish_time'),
                        'comments': data.get('comments'),
                        'image_files': image_files,
                        'entry_type': data.get('entry_type', 'Airscent'),
                        'update_time': session.update_time,
                        'uuid': session.uuid,
                        'status': data.get('status', 'active'),
                        'checksum': session.checksum,
                        'primary_timestamp': primary_ts,
                        'secondary_timestamp': secondary_ts,
                        'user_name': data.get('user_name', get_username())
                    })
                    
                    # Get the new session_id
                    result = conn.execute(text(
                        "SELECT id FROM training_sessions "
                        "WHERE session_number = :sn AND dog_name = :dn"
                    ), {'sn': sn, 'dn': session.dog_name})
                    row = result.fetchone()
                    session_id = row[0] if row else None
                
                # --- Write child tables ---
                if session_id:
                    self._write_airscent_child_tables(conn, session_id, data)
                
                conn.commit()
                return True
                
        except Exception as e:
            # print(f"Error upserting airscenting session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _write_airscent_child_tables(self, conn, session_id, data):
        """Write selected_terrains, subject_responses, a_selected_purposes for an airscent session.
        
        IMPORTANT: Only touches a child table if the source data explicitly
        contains the corresponding key.  Old JSON files that predate child-data
        support won't have these keys, and we must NOT delete the existing DB
        rows in that case.
        """
        from sqlalchemy import text
        from ui_utils import get_username
        user_name = data.get('user_name') or get_username()
        
        # --- selected_terrains ---
        if 'selected_terrains' in data:
            terrains = data['selected_terrains']
            conn.execute(text(
                "DELETE FROM selected_terrains WHERE session_id = :sid"
            ), {'sid': session_id})
            for terrain_name in terrains:
                conn.execute(text(
                    "INSERT INTO selected_terrains (session_id, terrain_name, user_name) "
                    "VALUES (:sid, :name, :user)"
                ), {'sid': session_id, 'name': terrain_name, 'user': user_name})
        
        # --- subject_responses ---
        if 'subject_responses' in data:
            responses = data['subject_responses']
            conn.execute(text(
                "DELETE FROM subject_responses WHERE session_id = :sid"
            ), {'sid': session_id})
            for resp in responses:
                conn.execute(text(
                    "INSERT INTO subject_responses (session_id, subject_number, tfr, refind, user_name) "
                    "VALUES (:sid, :num, :tfr, :refind, :user)"
                ), {
                    'sid': session_id,
                    'num': resp.get('subject_number', 0),
                    'tfr': resp.get('tfr', ''),
                    'refind': resp.get('refind', ''),
                    'user': user_name
                })
        
        # --- a_selected_purposes ---
        if 'selected_purposes' in data:
            purposes = data['selected_purposes']
            conn.execute(text(
                "DELETE FROM a_selected_purposes WHERE session_id = :sid"
            ), {'sid': session_id})
            for purpose_name in purposes:
                conn.execute(text(
                    "INSERT INTO a_selected_purposes (session_id, purpose_name, user_name) "
                    "VALUES (:sid, :name, :user)"
                ), {'sid': session_id, 'name': purpose_name, 'user': user_name})
    
    def _upsert_trailing_session(self, session: SessionInfo, primary_ts: Optional[datetime],
                                  secondary_ts: Optional[datetime]) -> bool:
        """Insert or update a trailing session, including child table data."""
        try:
            from sqlalchemy import text
            data = session.data
            
            # Ensure session_number is int (JSON might store as string)
            try:
                sn = int(session.session_number)
            except (ValueError, TypeError):
                print(f"Invalid trailing session_number: {session.session_number}")
                return False
            
            with self._get_connection() as conn:
                # Check if exists
                result = conn.execute(text("""
                    SELECT id FROM t_training_sessions 
                    WHERE t_session_number = :session_number AND t_dog_name = :dog_name
                """), {
                    'session_number': sn,
                    'dog_name': session.dog_name
                })
                existing = result.fetchone()
                
                # Prepare map_files as JSON string
                map_files = data.get('t_map_files', '')
                if isinstance(map_files, list):
                    map_files = json.dumps(map_files)
                
                if existing:
                    session_id = existing[0]
                    # Update
                    conn.execute(text("""
                        UPDATE t_training_sessions SET
                            t_date = :t_date, t_handler = :t_handler, t_field_support = :t_field_support,
                            t_location = :t_location, t_start_time = :t_start_time,
                            t_finish_time = :t_finish_time, t_trail_age = :t_trail_age,
                            t_trail_length = :t_trail_length, t_difficulty = :t_difficulty,
                            t_trail_layer = :t_trail_layer, t_cross_track_layer = :t_cross_track_layer,
                            t_cross_track_age = :t_cross_track_age,
                            t_weather_laying = :t_weather_laying, t_temperature_laying = :t_temperature_laying,
                            t_wind_speed_laying = :t_wind_speed_laying, t_wind_direction_laying = :t_wind_direction_laying,
                            t_humidity_laying = :t_humidity_laying,
                            t_weather_running = :t_weather_running, t_temperature_running = :t_temperature_running,
                            t_wind_speed_running = :t_wind_speed_running, t_wind_direction_running = :t_wind_direction_running,
                            t_humidity_running = :t_humidity_running,
                            t_start_behavior = :t_start_behavior, t_consistency = :t_consistency,
                            t_head_position = :t_head_position, t_pace = :t_pace, t_indication = :t_indication,
                            t_time_to_complete = :t_time_to_complete, t_success_rate = :t_success_rate,
                            t_impression = :t_impression, t_map_files = :t_map_files,
                            update_time = :update_time, uuid = :uuid, status = :status,
                            checksum = :checksum, primary_timestamp = :primary_timestamp,
                            secondary_timestamp = :secondary_timestamp,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE t_session_number = :t_session_number AND t_dog_name = :t_dog_name
                    """), {
                        't_date': data.get('t_date'),
                        't_handler': data.get('t_handler'),
                        't_field_support': data.get('t_field_support'),
                        't_location': data.get('t_location'),
                        't_start_time': data.get('t_start_time'),
                        't_finish_time': data.get('t_finish_time'),
                        't_trail_age': data.get('t_trail_age'),
                        't_trail_length': data.get('t_trail_length'),
                        't_difficulty': data.get('t_difficulty'),
                        't_trail_layer': data.get('t_trail_layer'),
                        't_cross_track_layer': data.get('t_cross_track_layer'),
                        't_cross_track_age': data.get('t_cross_track_age'),
                        't_weather_laying': data.get('t_weather_laying'),
                        't_temperature_laying': data.get('t_temperature_laying'),
                        't_wind_speed_laying': data.get('t_wind_speed_laying'),
                        't_wind_direction_laying': data.get('t_wind_direction_laying'),
                        't_humidity_laying': data.get('t_humidity_laying'),
                        't_weather_running': data.get('t_weather_running'),
                        't_temperature_running': data.get('t_temperature_running'),
                        't_wind_speed_running': data.get('t_wind_speed_running'),
                        't_wind_direction_running': data.get('t_wind_direction_running'),
                        't_humidity_running': data.get('t_humidity_running'),
                        't_start_behavior': data.get('t_start_behavior'),
                        't_consistency': data.get('t_consistency'),
                        't_head_position': data.get('t_head_position'),
                        't_pace': data.get('t_pace'),
                        't_indication': data.get('t_indication'),
                        't_time_to_complete': data.get('t_time_to_complete'),
                        't_success_rate': data.get('t_success_rate'),
                        't_impression': data.get('t_impression'),
                        't_map_files': map_files,
                        'update_time': session.update_time,
                        'uuid': session.uuid,
                        'status': data.get('status', 'active'),
                        'checksum': session.checksum,
                        'primary_timestamp': primary_ts,
                        'secondary_timestamp': secondary_ts,
                        't_session_number': sn,
                        't_dog_name': session.dog_name
                    })
                else:
                    # Insert
                    from ui_utils import get_username
                    conn.execute(text("""
                        INSERT INTO t_training_sessions 
                        (t_session_number, t_dog_name, t_date, t_handler, t_field_support,
                         t_location, t_start_time, t_finish_time, t_trail_age, t_trail_length,
                         t_difficulty, t_trail_layer, t_cross_track_layer, t_cross_track_age,
                         t_weather_laying, t_temperature_laying, t_wind_speed_laying, t_wind_direction_laying, t_humidity_laying,
                         t_weather_running, t_temperature_running, t_wind_speed_running, t_wind_direction_running, t_humidity_running,
                         t_start_behavior, t_consistency, t_head_position, t_pace, t_indication,
                         t_time_to_complete, t_success_rate, t_impression, t_map_files,
                         update_time, uuid, status, checksum, primary_timestamp, secondary_timestamp, user_name)
                        VALUES (:t_session_number, :t_dog_name, :t_date, :t_handler, :t_field_support,
                                :t_location, :t_start_time, :t_finish_time, :t_trail_age, :t_trail_length,
                                :t_difficulty, :t_trail_layer, :t_cross_track_layer, :t_cross_track_age,
                                :t_weather_laying, :t_temperature_laying, :t_wind_speed_laying, :t_wind_direction_laying, :t_humidity_laying,
                                :t_weather_running, :t_temperature_running, :t_wind_speed_running, :t_wind_direction_running, :t_humidity_running,
                                :t_start_behavior, :t_consistency, :t_head_position, :t_pace, :t_indication,
                                :t_time_to_complete, :t_success_rate, :t_impression, :t_map_files,
                                :update_time, :uuid, :status, :checksum, :primary_timestamp, :secondary_timestamp, :user_name)
                    """), {
                        't_session_number': sn,
                        't_dog_name': session.dog_name,
                        't_date': data.get('t_date'),
                        't_handler': data.get('t_handler'),
                        't_field_support': data.get('t_field_support'),
                        't_location': data.get('t_location'),
                        't_start_time': data.get('t_start_time'),
                        't_finish_time': data.get('t_finish_time'),
                        't_trail_age': data.get('t_trail_age'),
                        't_trail_length': data.get('t_trail_length'),
                        't_difficulty': data.get('t_difficulty'),
                        't_trail_layer': data.get('t_trail_layer'),
                        't_cross_track_layer': data.get('t_cross_track_layer'),
                        't_cross_track_age': data.get('t_cross_track_age'),
                        't_weather_laying': data.get('t_weather_laying'),
                        't_temperature_laying': data.get('t_temperature_laying'),
                        't_wind_speed_laying': data.get('t_wind_speed_laying'),
                        't_wind_direction_laying': data.get('t_wind_direction_laying'),
                        't_humidity_laying': data.get('t_humidity_laying'),
                        't_weather_running': data.get('t_weather_running'),
                        't_temperature_running': data.get('t_temperature_running'),
                        't_wind_speed_running': data.get('t_wind_speed_running'),
                        't_wind_direction_running': data.get('t_wind_direction_running'),
                        't_humidity_running': data.get('t_humidity_running'),
                        't_start_behavior': data.get('t_start_behavior'),
                        't_consistency': data.get('t_consistency'),
                        't_head_position': data.get('t_head_position'),
                        't_pace': data.get('t_pace'),
                        't_indication': data.get('t_indication'),
                        't_time_to_complete': data.get('t_time_to_complete'),
                        't_success_rate': data.get('t_success_rate'),
                        't_impression': data.get('t_impression'),
                        't_map_files': map_files,
                        'update_time': session.update_time,
                        'uuid': session.uuid,
                        'status': data.get('status', 'active'),
                        'checksum': session.checksum,
                        'primary_timestamp': primary_ts,
                        'secondary_timestamp': secondary_ts,
                        'user_name': data.get('user_name', get_username())
                    })
                    
                    # Get the new session_id
                    result = conn.execute(text(
                        "SELECT id FROM t_training_sessions "
                        "WHERE t_session_number = :sn AND t_dog_name = :dn"
                    ), {'sn': sn, 'dn': session.dog_name})
                    row = result.fetchone()
                    session_id = row[0] if row else None
                
                # --- Write child tables ---
                if session_id:
                    self._write_trailing_child_tables(conn, session_id, data)
                
                conn.commit()
                return True
                
        except Exception as e:
            # print(f"Error upserting trailing session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _write_trailing_child_tables(self, conn, session_id, data):
        """Write t_selected_terrains, t_selected_purposes, t_distractions for a trailing session.
        
        IMPORTANT: Only touches a child table if the source data explicitly
        contains the corresponding key.  Old JSON files that predate child-data
        support won't have these keys, and we must NOT delete the existing DB
        rows in that case.
        """
        from sqlalchemy import text
        from ui_utils import get_username
        user_name = data.get('user_name') or get_username()
        
        # --- t_selected_terrains ---
        if 't_selected_terrains' in data:
            terrains = data['t_selected_terrains']
            conn.execute(text(
                "DELETE FROM t_selected_terrains WHERE t_session_id = :sid"
            ), {'sid': session_id})
            for terrain_name in terrains:
                conn.execute(text(
                    "INSERT INTO t_selected_terrains (t_session_id, terrain_name, user_name) "
                    "VALUES (:sid, :name, :user)"
                ), {'sid': session_id, 'name': terrain_name, 'user': user_name})
        
        # --- t_selected_purposes ---
        if 't_selected_purposes' in data:
            purposes = data['t_selected_purposes']
            conn.execute(text(
                "DELETE FROM t_selected_purposes WHERE t_session_id = :sid"
            ), {'sid': session_id})
            for purpose_name in purposes:
                conn.execute(text(
                    "INSERT INTO t_selected_purposes (t_session_id, purpose_name, user_name) "
                    "VALUES (:sid, :name, :user)"
                ), {'sid': session_id, 'name': purpose_name, 'user': user_name})
        
        # --- t_distractions ---
        if 't_distractions' in data:
            distractions = data['t_distractions']
            conn.execute(text(
                "DELETE FROM t_distractions WHERE t_session_id = :sid"
            ), {'sid': session_id})
            for distraction in distractions:
                # Distraction data is stored as JSON string in the DB
                if isinstance(distraction, dict):
                    distraction_json = json.dumps(distraction)
                else:
                    distraction_json = str(distraction)
                conn.execute(text(
                    "INSERT INTO t_distractions (t_session_id, distraction_data, user_name) "
                    "VALUES (:sid, :data, :user)"
                ), {'sid': session_id, 'data': distraction_json, 'user': user_name})
    
    def update_timestamps(self, session: SessionInfo, primary_ts: Optional[datetime],
                         secondary_ts: Optional[datetime], checksum: str) -> bool:
        """Update just the timestamps and checksum for a session."""
        try:
            from sqlalchemy import text
            with self._get_connection() as conn:
                if session.session_type == 'a':
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
                        'session_number': session.session_number,
                        'dog_name': session.dog_name
                    })
                else:
                    conn.execute(text("""
                        UPDATE t_training_sessions SET
                            checksum = :checksum,
                            primary_timestamp = :primary_ts,
                            secondary_timestamp = :secondary_ts
                        WHERE t_session_number = :session_number AND t_dog_name = :dog_name
                    """), {
                        'checksum': checksum,
                        'primary_ts': primary_ts,
                        'secondary_ts': secondary_ts,
                        'session_number': session.session_number,
                        'dog_name': session.dog_name
                    })
                conn.commit()
                return True
        except Exception as e:
            # print(f"Error updating timestamps: {e}")
            return False
    
    def store_checksum(self, session_type: str, session_number: int,
                       dog_name: str, checksum: str) -> bool:
        """Store a content checksum for a session.
        
        Called after writing JSON so both DB and JSON have the same value.
        Also called after normal app saves (main + child tables).
        """
        try:
            from sqlalchemy import text
            with self._get_connection() as conn:
                if session_type == 'a':
                    conn.execute(text("""
                        UPDATE training_sessions SET checksum = :checksum
                        WHERE session_number = :sn AND dog_name = :dn
                    """), {'checksum': checksum, 'sn': session_number, 'dn': dog_name})
                else:
                    conn.execute(text("""
                        UPDATE t_training_sessions SET checksum = :checksum
                        WHERE t_session_number = :sn AND t_dog_name = :dn
                    """), {'checksum': checksum, 'sn': session_number, 'dn': dog_name})
                conn.commit()
                return True
        except Exception as e:
            # print(f"Error storing checksum: {e}")
            return False


# ==============================================================================
# JSON FILE OPERATIONS
# ==============================================================================

def scan_json_folder(folder_path: Path) -> Dict[str, SessionInfo]:
    """
    Scan a JSON folder and return sessions indexed by key.
    
    Args:
        folder_path: Path to JSON folder
        
    Returns:
        Dict mapping session key to SessionInfo
    """
    sessions = {}
    
    if not folder_path or not folder_path.exists():
        return sessions
    
    # Scan for JSON files with new naming convention
    for pattern in ['a_*.json', 't_*.json', '*_session_*.json']:
        for json_file in folder_path.glob(pattern):
            is_valid, data = validate_json_file(json_file)
            if not is_valid or data is None:
                continue
            
            # Determine session type and info from data
            if is_trailing_session(data):
                session_type = 't'
                dog_name = data.get('t_dog_name', 'unknown')
                try:
                    session_number = int(data.get('t_session_number', 0))
                except (ValueError, TypeError):
                    session_number = 0
            else:
                session_type = 'a'
                dog_name = data.get('dog_name', 'unknown')
                try:
                    session_number = int(data.get('session_number', 0))
                except (ValueError, TypeError):
                    session_number = 0
            
            # Parse update_time from data
            update_time = None
            update_time_str = data.get('update_time')
            if update_time_str:
                try:
                    update_time = datetime.fromisoformat(str(update_time_str).replace('Z', '+00:00'))
                except:
                    pass
            
            # Use stored content checksum if present (written by write_json_file).
            # Fall back to computing on-the-fly for legacy files without one.
            stored_checksum = data.get('checksum', '')
            if stored_checksum:
                checksum = stored_checksum
            else:
                checksum = compute_content_checksum(data)
            
            # Get user_name from data
            user_name = data.get('user_name', '')
            
            session = SessionInfo(
                session_type=session_type,
                dog_name=dog_name,
                session_number=session_number,
                uuid=data.get('uuid'),
                checksum=checksum,
                update_time=update_time,
                data=data,
                source='json',
                file_mtime=get_file_mtime(json_file),
                filepath=json_file,
                user_name=user_name
            )
            
            sessions[session.key] = session
    
    return sessions


def write_json_file(folder_path: Path, session: SessionInfo) -> Optional[datetime]:
    """
    Write session data to JSON file with consistent naming.
    
    Computes a content checksum and includes it in the JSON data.
    The same checksum should be stored in the DB so that on the next
    sync, a simple string comparison detects whether content differs.
    
    Args:
        folder_path: Path to JSON folder
        session: Session to write
        
    Returns:
        File modification timestamp after write, or None on failure
    """
    try:
        folder_path.mkdir(parents=True, exist_ok=True)
        
        filename = session.filename
        filepath = folder_path / filename
        
        # Write data as-is - do NOT modify update_time here.
        # update_time should only be set by the app when user saves/updates.
        data = session.data.copy()
        
        # Strip DB-specific fields that are meaningless in JSON backup.
        # 'id' is the auto-increment primary key — different on every machine.
        # 'primary_timestamp' and 'secondary_timestamp' are sync bookkeeping.
        for strip_key in ('id', 'primary_timestamp', 'secondary_timestamp'):
            data.pop(strip_key, None)
        
        # Compute content checksum from user data (excludes metadata)
        # and store it in the JSON so sync can compare stored values
        # instead of recomputing (which is fragile due to normalization).
        content_checksum = compute_content_checksum(data)
        data['checksum'] = content_checksum
        
        # Also update the session object so callers can store it in DB
        session.checksum = content_checksum
        
        # Write file - ensure_ascii=False preserves unicode characters
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        
        # Get and return file modification time
        return get_file_mtime(filepath)
        
    except Exception as e:
        # print(f"Error writing JSON file: {e}")
        return None


def rename_legacy_json_file(filepath: Path, session: SessionInfo) -> Optional[Path]:
    """
    Rename a legacy JSON file to the new naming convention.
    
    Args:
        filepath: Current file path
        session: Session info for new filename
        
    Returns:
        New file path, or None on failure
    """
    try:
        new_filename = session.filename
        new_filepath = filepath.parent / new_filename
        
        if filepath != new_filepath:
            shutil.move(str(filepath), str(new_filepath))
            # print(f"Renamed: {filepath.name} -> {new_filename}")
            return new_filepath
        
        return filepath
        
    except Exception as e:
        # print(f"Error renaming file: {e}")
        return None


# ==============================================================================
# SYNC MANAGER
# ==============================================================================

class BackupSyncManager:
    """
    Manages synchronization between database and JSON backups.
    
    Sync algorithm:
    1. Scan all sources (DB, primary JSON, secondary JSON)
    2. For each unique session, determine authoritative source:
       - If checksums match across sources, they're in sync
       - If checksums differ, use most recent file modification time
       - New sessions from secondary (network) get added to primary and DB
    3. Update all locations to match authoritative source
    4. Update checksums and timestamps in DB
    """
    
    def __init__(self, db_type: str, primary_folder: Optional[Path] = None,
                 secondary_folder: Optional[Path] = None):
        self.db_type = db_type
        self.primary_folder = Path(primary_folder) if primary_folder else None
        self.secondary_folder = Path(secondary_folder) if secondary_folder else None
        self.db_ops = DatabaseOps(db_type)
        self.sync_results = {
            'db_updates': 0,
            'primary_writes': 0,
            'secondary_writes': 0,
            'renames': 0,
            'errors': []
        }
    
    def _ensure_backup_folders_exist(self, status) -> None:
        """
        Ensure JSON and Images folders exist within backup folders.
        Creates them if backup folder exists but subfolders don't.
        """
        folders_to_check = [
            (self.primary_folder, "Primary"),
            (self.secondary_folder, "Secondary")
        ]
        
        for json_folder, label in folders_to_check:
            if json_folder is None:
                continue
                
            # json_folder is the JSON subfolder - get parent backup folder
            backup_folder = json_folder.parent
            
            if not backup_folder.exists():
                # Backup folder doesn't exist - skip (user needs to create it)
                continue
            
            # Check/create JSON folder
            if not json_folder.exists():
                try:
                    json_folder.mkdir(parents=True, exist_ok=True)
                    status(f"{label} JSON folder created: {json_folder}")
                except Exception as e:
                    status(f"Warning: Could not create {label} JSON folder: {e}")
            
            # Check/create Images folder (sibling to JSON folder)
            images_folder = backup_folder / "Images"
            if not images_folder.exists():
                try:
                    images_folder.mkdir(parents=True, exist_ok=True)
                    status(f"{label} Images folder created: {images_folder}")
                except Exception as e:
                    status(f"Warning: Could not create {label} Images folder: {e}")
    
    def perform_full_sync(self, status_callback=None, conflict_callback=None) -> dict:
        """
        Perform complete synchronization.
        
        Simplified approach - compares local (DB) vs remote (secondary) per session:
        - Same checksum → skip (in sync)
        - Different checksum → conflict, ask user
        - New in remote only → import
        - New in local only → push to secondary
        Primary JSON simply mirrors the DB after all decisions are made.
        
        Args:
            status_callback: Optional function to report status messages
            conflict_callback: Optional function called with list of conflicts.
                Must return list of resolution dicts with 'key' and 'action' 
                ('use_remote', 'use_local', 'skip')
            
        Returns:
            Dict with sync results
        """
        self.sync_results = {
            'db_updates': 0,
            'primary_writes': 0,
            'secondary_writes': 0,
            'renames': 0,
            'new_from_remote': 0,
            'conflicts_resolved': 0,
            'db_backup_path': None,
            'errors': []
        }
        
        def status(msg):
            # print(f"Sync: {msg}")
            if status_callback:
                status_callback(msg)
        
        # Ensure JSON and Images folders exist if backup folders exist
        self._ensure_backup_folders_exist(status)
        
        # Check database health
        db_healthy = self.db_ops.is_db_healthy()
        
        if not db_healthy:
            status("Database appears damaged - will rebuild from backups")
            return self._rebuild_from_backups(status)
        
        # --- Scan all sources (read-only) ---
        status("Scanning database...")
        db_sessions = {s.key: s for s in self.db_ops.get_all_sessions()}
        
        status("Scanning secondary backup...")
        secondary_sessions = scan_json_folder(self.secondary_folder) if self.secondary_folder else {}
        
        # --- Ensure all DB sessions have content checksums ---
        # First sync after upgrade: DB checksum column may be NULL.
        # Compute and store now so future comparisons are instant.
        for key, session in db_sessions.items():
            if not session.checksum:
                checksum = compute_content_checksum(session.data)
                session.checksum = checksum
                self.db_ops.store_checksum(
                    session.session_type, session.session_number,
                    session.dog_name, checksum)
        
        # --- Compare DB (local) vs Secondary (remote) per session ---
        local_keys = set(db_sessions.keys())
        remote_keys = set(secondary_sessions.keys())
        
        # Sessions only in local → will push to secondary later
        local_only = local_keys - remote_keys
        
        # Sessions only in remote → new, import them
        remote_only = remote_keys - local_keys
        
        # Sessions in both → compare stored checksums
        shared_keys = local_keys & remote_keys
        
        conflicts = []
        in_sync_count = 0
        
        for key in shared_keys:
            local_session = db_sessions[key]
            remote_session = secondary_sessions[key]
            
            # Compare stored content checksums.
            # Both were computed by compute_content_checksum() and stored
            # at write time, so they match unless content genuinely differs.
            local_checksum = local_session.checksum or ''
            remote_checksum = remote_session.checksum or ''
            
            if local_checksum and remote_checksum and local_checksum == remote_checksum:
                in_sync_count += 1
            else:
                # Checksums differ → real content conflict, user must decide.
                # Show update_time so user knows which is newer.
                local_time = local_session.update_time or datetime.min
                remote_time = remote_session.update_time or remote_session.file_mtime or datetime.min
                
                local_time_str = local_time.strftime('%Y-%m-%d %H:%M:%S') if local_time != datetime.min else 'unknown'
                remote_time_str = remote_time.strftime('%Y-%m-%d %H:%M:%S') if remote_time != datetime.min else 'unknown'
                
                dog = local_session.dog_name
                num = local_session.session_number
                stype = "Trailing" if local_session.session_type == 't' else "Airscent"
                
                conflicts.append({
                    'key': key,
                    'local': local_session,
                    'remote': remote_session,
                    'conflict_type': 'modified',
                    'description': (
                        f"{stype} session #{num} for {dog}:\n"
                        f"  Local updated:  {local_time_str}\n"
                        f"  Remote updated: {remote_time_str}\n"
                        f"  Content differs between local database and remote backup."
                    )
                })
        
        status(f"Found {in_sync_count} in sync, {len(conflicts)} conflict(s), "
               f"{len(remote_only)} new remote, {len(local_only)} local only")
        
        # --- Resolve conflicts with user ---
        resolutions = {}
        if conflicts and conflict_callback:
            status(f"Found {len(conflicts)} conflict(s) requiring your input...")
            resolutions_list = conflict_callback(conflicts)
            if resolutions_list:
                for resolution in resolutions_list:
                    resolutions[resolution['key']] = resolution['action']
        
        # --- Determine if DB changes are needed before touching anything ---
        db_will_change = len(remote_only) > 0
        if not db_will_change:
            for conflict in conflicts:
                if resolutions.get(conflict['key']) == 'use_remote':
                    db_will_change = True
                    break
        
        # Only backup DB when we are actually going to modify it
        if db_will_change:
            db_backup_path = self._backup_database(status)
            self.sync_results['db_backup_path'] = str(db_backup_path) if db_backup_path else None
        
        # --- Apply conflict resolutions ---
        for conflict in conflicts:
            key = conflict['key']
            action = resolutions.get(key, 'skip')
            self._apply_conflict_resolution(conflict, action, status)
        
        # --- Import new remote sessions ---
        for key in remote_only:
            remote_session = secondary_sessions[key]
            if self.db_ops.upsert_session(remote_session, None, remote_session.file_mtime):
                self.sync_results['db_updates'] += 1
                self.sync_results['new_from_remote'] += 1
                dog = remote_session.dog_name
                num = remote_session.session_number
                status(f"Imported from remote: session #{num} for {dog}")
        
        # --- Push local-only sessions to secondary ---
        if self.secondary_folder:
            for key in local_only:
                local_session = db_sessions[key]
                ts = write_json_file(self.secondary_folder, local_session)
                if ts:
                    self.sync_results['secondary_writes'] += 1
                    # write_json_file computed and stored the checksum on
                    # the session object — store the same value in DB so
                    # next sync comparison uses identical stored checksums.
                    if local_session.checksum:
                        self.db_ops.store_checksum(
                            local_session.session_type,
                            local_session.session_number,
                            local_session.dog_name,
                            local_session.checksum)
        
        # --- Mirror DB state to primary JSON ---
        # Re-read DB to get current state after any updates
        if self.primary_folder:
            status("Updating primary backup...")
            current_db = {s.key: s for s in self.db_ops.get_all_sessions()}
            primary_sessions = scan_json_folder(self.primary_folder) if self.primary_folder else {}
            
            for key, db_session in current_db.items():
                primary_session = primary_sessions.get(key)
                
                if primary_session is None:
                    # Missing from primary → write it
                    ts = write_json_file(self.primary_folder, db_session)
                    if ts:
                        self.sync_results['primary_writes'] += 1
                else:
                    # Force-rewrite old-format files that lack a stored checksum.
                    # This ensures child table data (terrains, purposes, responses,
                    # distractions) gets written to JSON files that predate this support.
                    primary_has_stored_checksum = bool(
                        primary_session.data and primary_session.data.get('checksum'))
                    
                    # Check if primary matches DB using stored checksums
                    db_checksum = db_session.checksum or ''
                    primary_checksum = primary_session.checksum or ''
                    
                    if (not primary_has_stored_checksum
                            or not db_checksum
                            or not primary_checksum
                            or db_checksum != primary_checksum):
                        ts = write_json_file(self.primary_folder, db_session)
                        if ts:
                            self.sync_results['primary_writes'] += 1
                    elif primary_session.filepath and primary_session.filepath.name != db_session.filename:
                        # Rename legacy file to new convention
                        new_path = rename_legacy_json_file(primary_session.filepath, db_session)
                        if new_path:
                            self.sync_results['renames'] += 1
        
        # Sync images between primary and secondary
        status("Synchronizing images...")
        image_sync_count = self._sync_images(status)
        self.sync_results['images_synced'] = image_sync_count
        
        status(f"Sync complete: {self.sync_results}")
        return self.sync_results
    
    def _backup_database(self, status) -> Optional[Path]:
        """
        Create a backup copy of the database before sync.
        Returns the path to the backup, or None on failure.
        """
        try:
            import config
            if config.DB_TYPE != 'sqlite':
                status("DB backup: Skipping (non-SQLite database)")
                return None
            
            db_url = config.DB_CONFIG.get('sqlite', {}).get('url', '')
            db_path_str = db_url.replace('sqlite:///', '')
            if not db_path_str:
                return None
            
            db_path = Path(db_path_str)
            if not db_path.exists():
                return None
            
            # Create backup with unique timestamp name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{db_path.stem}_presync_{timestamp}{db_path.suffix}"
            backup_path = db_path.parent / backup_name
            
            shutil.copy2(str(db_path), str(backup_path))
            status(f"Database backed up to: {backup_name}")
            return backup_path
            
        except Exception as e:
            status(f"Warning: Could not backup database: {e}")
            self.sync_results['errors'].append(f"DB backup failed: {e}")
            return None
    
    def _apply_conflict_resolution(self, conflict, action, status):
        """Apply user's conflict resolution decision."""
        key = conflict['key']
        local_session = conflict.get('local')
        remote_session = conflict.get('remote')
        
        if action == 'skip':
            status(f"Skipped: {key}")
            return
        
        if action == 'use_local':
            # Keep local version, push to secondary to overwrite remote
            if local_session and self.secondary_folder:
                ts = write_json_file(self.secondary_folder, local_session)
                if ts:
                    self.sync_results['secondary_writes'] += 1
                    # Store matching checksum in DB
                    if local_session.checksum:
                        self.db_ops.store_checksum(
                            local_session.session_type,
                            local_session.session_number,
                            local_session.dog_name,
                            local_session.checksum)
            status(f"Kept local: {key}")
            self.sync_results['conflicts_resolved'] += 1
            return
        
        if action == 'use_remote':
            # Accept remote version into DB
            if remote_session:
                secondary_ts = remote_session.file_mtime
                
                if self.db_ops.upsert_session(remote_session, None, secondary_ts):
                    self.sync_results['db_updates'] += 1
                    # Store the remote checksum in DB so they match
                    if remote_session.checksum:
                        self.db_ops.store_checksum(
                            remote_session.session_type,
                            remote_session.session_number,
                            remote_session.dog_name,
                            remote_session.checksum)
                
                status(f"Used remote: {key}")
            self.sync_results['conflicts_resolved'] += 1
            return
    
    def _sync_images(self, status) -> int:
        """
        Sync images between primary and secondary Images folders.
        Copies any image that exists in one folder but not the other.
        
        Returns:
            Number of images copied
        """
        count = 0
        
        # Get Images folder paths
        primary_images = self.primary_folder.parent / "Images" if self.primary_folder else None
        secondary_images = self.secondary_folder.parent / "Images" if self.secondary_folder else None
        
        if not primary_images or not primary_images.exists():
            return count
        
        if not secondary_images:
            return count
        
        # Create secondary Images folder if needed
        if not secondary_images.exists():
            try:
                secondary_images.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                # print(f"Could not create secondary Images folder: {e}")
                return count
        
        # Image extensions to sync
        image_extensions = {'.jpg', '.jpeg', '.png', '.pdf', '.gif', '.bmp'}
        
        # Get files in each folder
        primary_files = {}
        for f in primary_images.iterdir():
            if f.is_file() and f.suffix.lower() in image_extensions:
                primary_files[f.name] = f
        
        secondary_files = {}
        for f in secondary_images.iterdir():
            if f.is_file() and f.suffix.lower() in image_extensions:
                secondary_files[f.name] = f
        
        # Copy missing files from primary to secondary
        for name, filepath in primary_files.items():
            if name not in secondary_files:
                try:
                    dest = secondary_images / name
                    shutil.copy2(str(filepath), str(dest))
                    count += 1
                    # print(f"  Copied image to secondary: {name}")
                    pass
                except Exception as e:
                    # print(f"  Error copying {name} to secondary: {e}")
                    pass
        
        # Copy missing files from secondary to primary
        for name, filepath in secondary_files.items():
            if name not in primary_files:
                try:
                    dest = primary_images / name
                    shutil.copy2(str(filepath), str(dest))
                    count += 1
                    # print(f"  Copied image to primary: {name}")
                    pass
                except Exception as e:
                    # print(f"  Error copying {name} to primary: {e}")
                    pass
        
        if count > 0:
            status(f"Synced {count} image(s)")
        
        return count
    
    def _sync_session(self, key: str, db_session: Optional[SessionInfo],
                      primary_session: Optional[SessionInfo],
                      secondary_session: Optional[SessionInfo],
                      status) -> None:
        """Synchronize a single session across all sources."""
        
        # Determine authoritative source
        auth_session, auth_source = self._determine_authority(
            db_session, primary_session, secondary_session
        )
        
        if auth_session is None:
            return
        
        # Track timestamps for DB
        primary_ts = primary_session.file_mtime if primary_session else None
        secondary_ts = secondary_session.file_mtime if secondary_session else None
        
        # Update DB if needed
        if db_session is None or db_session.checksum != auth_session.checksum:
            if self.db_ops.upsert_session(auth_session, primary_ts, secondary_ts):
                self.sync_results['db_updates'] += 1
                status(f"Updated DB: {key}")
        else:
            # Just update timestamps if checksums match
            self.db_ops.update_timestamps(db_session, primary_ts, secondary_ts, auth_session.checksum)
        
        # Update primary JSON if needed
        if self.primary_folder:
            if primary_session is None or primary_session.checksum != auth_session.checksum:
                ts = write_json_file(self.primary_folder, auth_session)
                if ts:
                    self.sync_results['primary_writes'] += 1
                    primary_ts = ts
            elif primary_session.filepath and primary_session.filepath.name != auth_session.filename:
                # Rename to new convention
                new_path = rename_legacy_json_file(primary_session.filepath, auth_session)
                if new_path:
                    self.sync_results['renames'] += 1
        
        # Update secondary JSON if needed
        if self.secondary_folder:
            if secondary_session is None or secondary_session.checksum != auth_session.checksum:
                ts = write_json_file(self.secondary_folder, auth_session)
                if ts:
                    self.sync_results['secondary_writes'] += 1
                    secondary_ts = ts
            elif secondary_session.filepath and secondary_session.filepath.name != auth_session.filename:
                # Rename to new convention
                new_path = rename_legacy_json_file(secondary_session.filepath, auth_session)
                if new_path:
                    self.sync_results['renames'] += 1
        
        # Final timestamp update in DB
        self.db_ops.update_timestamps(auth_session, primary_ts, secondary_ts, auth_session.checksum)
    
    def _determine_authority(self, db_session: Optional[SessionInfo],
                             primary_session: Optional[SessionInfo],
                             secondary_session: Optional[SessionInfo]) -> Tuple[Optional[SessionInfo], str]:
        """
        Determine which source has the authoritative version.
        
        Priority:
        1. If only one source exists, use it
        2. If checksums match, use DB (or primary if no DB)
        3. If checksums differ, compare using update_time from session data first
           (set by the app when saving), then fall back to file_mtime.
           This handles cross-machine scenarios where file_mtime may be unreliable.
        """
        sources = []
        if db_session:
            sources.append(('db', db_session))
        if primary_session:
            sources.append(('primary', primary_session))
        if secondary_session:
            sources.append(('secondary', secondary_session))
        
        if not sources:
            return None, ''
        
        if len(sources) == 1:
            return sources[0][1], sources[0][0]
        
        # Check if all checksums match
        checksums = set()
        for source_name, session in sources:
            if session.checksum:
                checksums.add(session.checksum)
        
        if len(checksums) == 1:
            # All match - prefer DB
            if db_session:
                return db_session, 'db'
            return sources[0][1], sources[0][0]
        
        # Checksums differ - find most recent version
        # Use update_time from session data (set by the saving app) as primary indicator.
        # Fall back to file_mtime only when update_time is missing.
        def get_best_time(source_name, session):
            """Get the best available timestamp for comparison."""
            # Prefer update_time from the data itself (set by the saving app)
            if session.update_time:
                return session.update_time
            # Fall back to file modification time for JSON sources
            if source_name != 'db' and session.file_mtime:
                return session.file_mtime
            return datetime.min
        
        # Sort all sources by best timestamp, most recent first
        sources.sort(key=lambda x: get_best_time(x[0], x[1]), reverse=True)
        
        winner_name, winner_session = sources[0]
        return winner_session, winner_name
    
    def _rebuild_from_backups(self, status) -> dict:
        """Rebuild database from JSON backups."""
        status("Rebuilding database from backups...")
        
        # Scan both backup folders
        primary_sessions = scan_json_folder(self.primary_folder) if self.primary_folder else {}
        secondary_sessions = scan_json_folder(self.secondary_folder) if self.secondary_folder else {}
        
        all_keys = set(primary_sessions.keys()) | set(secondary_sessions.keys())
        
        status(f"Found {len(all_keys)} sessions in backups")
        
        for key in all_keys:
            primary_session = primary_sessions.get(key)
            secondary_session = secondary_sessions.get(key)
            
            # Choose the more recent one
            if primary_session and secondary_session:
                p_time = primary_session.update_time or primary_session.file_mtime or datetime.min
                s_time = secondary_session.update_time or secondary_session.file_mtime or datetime.min
                
                if s_time > p_time:
                    auth_session = secondary_session
                else:
                    auth_session = primary_session
            else:
                auth_session = primary_session or secondary_session
            
            if auth_session:
                primary_ts = primary_session.file_mtime if primary_session else None
                secondary_ts = secondary_session.file_mtime if secondary_session else None
                
                if self.db_ops.upsert_session(auth_session, primary_ts, secondary_ts):
                    self.sync_results['db_updates'] += 1
                    status(f"Restored: {key}")
                
                # Ensure both backups have the file
                if self.primary_folder and not primary_session:
                    write_json_file(self.primary_folder, auth_session)
                    self.sync_results['primary_writes'] += 1
                
                if self.secondary_folder and not secondary_session:
                    write_json_file(self.secondary_folder, auth_session)
                    self.sync_results['secondary_writes'] += 1
        
        # Also sync images during rebuild
        status("Synchronizing images...")
        image_sync_count = self._sync_images(status)
        self.sync_results['images_synced'] = image_sync_count
        
        return self.sync_results


# ==============================================================================
# SESSION CHECKSUM HELPER
# ==============================================================================

def update_session_checksum(db_type: str, session_type: str,
                            session_number: int, dog_name: str) -> Optional[str]:
    """
    Compute checksum and write JSON backups for a session after saving.
    
    Call this AFTER saving the main session AND all child tables
    (terrains, purposes, responses, distractions).  It will:
    
    1. Load the full session (main + child tables) from the DB.
    2. Compute a content checksum over all user data.
    3. Store the checksum in the DB's ``checksum`` column.
    4. Write JSON backup files (primary and secondary) so they are
       always up-to-date — not just after the next startup sync.
    
    Args:
        db_type: Database type ('sqlite', 'postgres', etc.)
        session_type: 'a' for airscenting, 't' for trailing
        session_number: Session number
        dog_name: Dog name
        
    Returns:
        The computed checksum string, or None on failure
    """
    try:
        db_ops = DatabaseOps(db_type)
        
        # Load the full session (main table + child tables) from DB
        # so the checksum covers all user data.
        all_sessions = db_ops.get_all_sessions()
        
        target_key = f"{session_type}_{dog_name}_{session_number}"
        target_session = None
        for s in all_sessions:
            if s.key == target_key:
                target_session = s
                break
        
        if not target_session or not target_session.data:
            return None
        
        # Compute and store checksum in DB
        checksum = compute_content_checksum(target_session.data)
        db_ops.store_checksum(session_type, session_number, dog_name, checksum)
        target_session.checksum = checksum
        
        # Write JSON backups immediately so they stay in sync with the DB.
        # Without this, JSON only updates at next startup sync, meaning
        # child table data (terrains, purposes, responses, distractions)
        # would be missing from JSON until then.
        try:
            from ui_utils import get_primary_json_folder, get_secondary_json_folder
            
            primary_folder = get_primary_json_folder()
            if primary_folder:
                write_json_file(primary_folder, target_session)
            
            secondary_folder = get_secondary_json_folder()
            if secondary_folder:
                write_json_file(secondary_folder, target_session)
        except Exception as e:
            # JSON write failure is non-fatal — sync will catch up later
            print(f"Warning: Could not write JSON backup: {e}")
        
        return checksum
        
    except Exception as e:
        # print(f"Error updating session checksum: {e}")
        return None


# ==============================================================================
# SAVE SESSION HELPER
# ==============================================================================

def save_session_with_backup(session_data: dict, session_type: str, 
                             db_type: str, primary_folder: Optional[Path],
                             secondary_folder: Optional[Path]) -> Tuple[bool, str, Optional[str]]:
    """
    Save a session to database and create JSON backups with checksums.
    
    This should be called after successfully saving to the database.
    
    Args:
        session_data: Session data dict
        session_type: 'a' for airscenting, 't' for trailing
        db_type: Database type
        primary_folder: Primary JSON backup folder
        secondary_folder: Secondary JSON backup folder (optional)
        
    Returns:
        Tuple of (success, message, checksum)
    """
    import uuid as uuid_lib
    
    # Ensure UUID exists
    if not session_data.get('uuid'):
        session_data['uuid'] = str(uuid_lib.uuid4())
    
    # Set update time
    session_data['update_time'] = datetime.now().isoformat()
    
    # Compute checksum
    checksum = compute_checksum(session_data)
    
    # Determine dog name, session number, and user_name
    user_name = session_data.get('user_name', '')
    if session_type == 't':
        dog_name = session_data.get('t_dog_name', 'unknown')
        session_number = session_data.get('t_session_number', 0)
    else:
        dog_name = session_data.get('dog_name', 'unknown')
        session_number = session_data.get('session_number', 0)
    
    # Create SessionInfo
    session = SessionInfo(
        session_type=session_type,
        dog_name=dog_name,
        session_number=session_number,
        uuid=session_data.get('uuid'),
        checksum=checksum,
        update_time=datetime.now(),
        data=session_data,
        source='app',
        user_name=user_name
    )
    
    primary_ts = None
    secondary_ts = None
    
    # Write to primary
    if primary_folder:
        primary_ts = write_json_file(Path(primary_folder), session)
        if not primary_ts:
            return False, "Failed to write primary backup", None
    
    # Write to secondary
    if secondary_folder:
        secondary_ts = write_json_file(Path(secondary_folder), session)
        # Non-fatal if secondary write fails
    
    # Update timestamps in DB
    db_ops = DatabaseOps(db_type)
    db_ops.update_timestamps(session, primary_ts, secondary_ts, checksum)
    
    return True, "Backup saved successfully", checksum


# ==============================================================================
# GLOBAL INSTANCE
# ==============================================================================

_sync_manager = None

def get_sync_manager(db_type: str = None, primary_folder: Path = None,
                     secondary_folder: Path = None) -> BackupSyncManager:
    """Get or create the global sync manager."""
    global _sync_manager
    
    if _sync_manager is None or db_type:
        _sync_manager = BackupSyncManager(
            db_type or 'sqlite',
            primary_folder,
            secondary_folder
        )
    
    return _sync_manager
