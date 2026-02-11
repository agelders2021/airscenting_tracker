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
Database schema for Air-Scenting Logger
Defines tables and creates them in the database
"""
from sqlalchemy import text
from database import engine, get_connection
from config import DB_TYPE


def create_tables():
    """Create all database tables"""
    
    # Auto-increment syntax differs between databases
    if DB_TYPE == "sqlite":
        dog_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        session_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        settings_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        location_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        terrain_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        distraction_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        selected_terrain_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        subject_response_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        a_selected_purpose_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        # Trailing session tables
        t_session_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        t_selected_terrain_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        t_selected_purpose_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        t_distraction_id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
    else:  # postgres or supabase
        dog_id_type = "SERIAL PRIMARY KEY"
        session_id_type = "SERIAL PRIMARY KEY"
        settings_id_type = "SERIAL PRIMARY KEY"
        location_id_type = "SERIAL PRIMARY KEY"
        terrain_id_type = "SERIAL PRIMARY KEY"
        distraction_id_type = "SERIAL PRIMARY KEY"
        selected_terrain_id_type = "SERIAL PRIMARY KEY"
        subject_response_id_type = "SERIAL PRIMARY KEY"
        a_selected_purpose_id_type = "SERIAL PRIMARY KEY"
        # Trailing session tables
        t_session_id_type = "SERIAL PRIMARY KEY"
        t_selected_terrain_id_type = "SERIAL PRIMARY KEY"
        t_selected_purpose_id_type = "SERIAL PRIMARY KEY"
        t_distraction_id_type = "SERIAL PRIMARY KEY"
    
    # Settings table (for database-specific settings like last dog)
    settings_table = f"""
    CREATE TABLE IF NOT EXISTS settings (
        id {settings_id_type},
        key TEXT NOT NULL UNIQUE,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # Dogs table
    dogs_table = f"""
    CREATE TABLE IF NOT EXISTS dogs (
        id {dog_id_type},
        name TEXT NOT NULL UNIQUE,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # Training locations table
    locations_table = f"""
    CREATE TABLE IF NOT EXISTS training_locations (
        id {location_id_type},
        name TEXT NOT NULL UNIQUE,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # Terrain types table
    terrain_table = f"""
    CREATE TABLE IF NOT EXISTS terrain_types (
        id {terrain_id_type},
        name TEXT NOT NULL UNIQUE,
        user_name TEXT,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # Distraction types table
    distraction_table = f"""
    CREATE TABLE IF NOT EXISTS distraction_types (
        id {distraction_id_type},
        name TEXT NOT NULL UNIQUE,
        user_name TEXT,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # Training sessions table
    sessions_table = f"""
    CREATE TABLE IF NOT EXISTS training_sessions (
        id {session_id_type},
        date DATE NOT NULL,
        session_number INTEGER NOT NULL,
        handler TEXT,
        session_purpose TEXT,
        field_support TEXT,
        dog_name TEXT,
        location TEXT,
        search_area_size TEXT,
        num_subjects TEXT,
        handler_knowledge TEXT,
        weather TEXT,
        temperature TEXT,
        wind_direction TEXT,
        wind_speed TEXT,
        search_type TEXT,
        drive_level TEXT,
        subjects_found TEXT,
        a_percent_searched TEXT,
        start_time TEXT,
        finish_time TEXT,
        comments TEXT,
        image_files TEXT,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        entry_type TEXT,
        update_time TIMESTAMP,
        uuid TEXT,
        status TEXT DEFAULT 'active',
        checksum TEXT,
        primary_timestamp TIMESTAMP,
        secondary_timestamp TIMESTAMP,
        UNIQUE(session_number, dog_name)
    )
    """
    
    # Selected terrains table (many-to-many: sessions to terrain types)
    selected_terrains_table = f"""
    CREATE TABLE IF NOT EXISTS selected_terrains (
        id {selected_terrain_id_type},
        session_id INTEGER NOT NULL,
        terrain_name TEXT NOT NULL,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
    )
    """
    
    # Subject responses table (one-to-many: sessions to subject responses)
    subject_responses_table = f"""
    CREATE TABLE IF NOT EXISTS subject_responses (
        id {subject_response_id_type},
        session_id INTEGER NOT NULL,
        subject_number INTEGER NOT NULL,
        tfr TEXT,
        refind TEXT,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
    )
    """
    
    # Airscenting selected purposes table (many-to-many: sessions to purposes)
    a_selected_purposes_table = f"""
    CREATE TABLE IF NOT EXISTS a_selected_purposes (
        id {a_selected_purpose_id_type},
        session_id INTEGER NOT NULL,
        purpose_name TEXT NOT NULL,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
    )
    """
    
    # =========================================================================
    # TRAILING SESSION TABLES
    # =========================================================================
    
    # Trailing training sessions table
    t_sessions_table = f"""
    CREATE TABLE IF NOT EXISTS t_training_sessions (
        id {t_session_id_type},
        t_date DATE NOT NULL,
        t_session_number INTEGER NOT NULL,
        t_handler TEXT,
        t_field_support TEXT,
        t_dog_name TEXT,
        t_location TEXT,
        t_start_time TEXT,
        t_finish_time TEXT,
        t_trail_age TEXT,
        t_trail_length TEXT,
        t_difficulty TEXT,
        t_trail_layer TEXT,
        t_cross_track_layer TEXT,
        t_cross_track_age TEXT,
        t_weather_laying TEXT,
        t_temperature_laying TEXT,
        t_wind_speed_laying TEXT,
        t_wind_direction_laying TEXT,
        t_humidity_laying TEXT,
        t_weather_running TEXT,
        t_temperature_running TEXT,
        t_wind_speed_running TEXT,
        t_wind_direction_running TEXT,
        t_humidity_running TEXT,
        t_start_behavior TEXT,
        t_consistency TEXT,
        t_head_position TEXT,
        t_pace TEXT,
        t_indication TEXT,
        t_time_to_complete TEXT,
        t_success_rate TEXT,
        t_impression TEXT,
        t_map_files TEXT,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        entry_type TEXT,
        update_time TIMESTAMP,
        uuid TEXT,
        status TEXT DEFAULT 'active',
        checksum TEXT,
        primary_timestamp TIMESTAMP,
        secondary_timestamp TIMESTAMP,
        UNIQUE(t_session_number, t_dog_name)
    )
    """
    
    # Trailing selected terrains table (many-to-many: t_sessions to terrain types)
    t_selected_terrains_table = f"""
    CREATE TABLE IF NOT EXISTS t_selected_terrains (
        id {t_selected_terrain_id_type},
        t_session_id INTEGER NOT NULL,
        terrain_name TEXT NOT NULL,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (t_session_id) REFERENCES t_training_sessions(id) ON DELETE CASCADE
    )
    """
    
    # Trailing selected purposes table (many-to-many: t_sessions to purposes)
    t_selected_purposes_table = f"""
    CREATE TABLE IF NOT EXISTS t_selected_purposes (
        id {t_selected_purpose_id_type},
        t_session_id INTEGER NOT NULL,
        purpose_name TEXT NOT NULL,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (t_session_id) REFERENCES t_training_sessions(id) ON DELETE CASCADE
    )
    """
    
    # Trailing distractions table (one-to-many: t_sessions to distractions as JSON)
    t_distractions_table = f"""
    CREATE TABLE IF NOT EXISTS t_distractions (
        id {t_distraction_id_type},
        t_session_id INTEGER NOT NULL,
        distraction_data TEXT NOT NULL,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (t_session_id) REFERENCES t_training_sessions(id) ON DELETE CASCADE
    )
    """
    
    with get_connection() as conn:
        # Create settings table
        conn.execute(text(settings_table))
        # Create dogs table
        conn.execute(text(dogs_table))
        # Create training_locations table
        conn.execute(text(locations_table))
        # Create terrain_types table
        conn.execute(text(terrain_table))
        # Create distraction_types table
        conn.execute(text(distraction_table))
        # Create training_sessions table
        conn.execute(text(sessions_table))
        # Create selected_terrains table
        conn.execute(text(selected_terrains_table))
        # Create subject_responses table
        conn.execute(text(subject_responses_table))
        # Create a_selected_purposes table (airscenting purposes)
        conn.execute(text(a_selected_purposes_table))
        
        # Create trailing session tables
        conn.execute(text(t_sessions_table))
        conn.execute(text(t_selected_terrains_table))
        conn.execute(text(t_selected_purposes_table))
        conn.execute(text(t_distractions_table))
        
        conn.commit()
        
        print("Database tables created successfully")
    
    # Run migrations to add any new columns to existing databases
    # These are safe to run multiple times - they check if columns exist first
    migrate_add_backup_columns()
    migrate_add_a_selected_purposes_table()
    migrate_add_a_percent_searched_column()
    add_missing_columns_to_t_training_sessions()


def drop_tables():
    """Drop all tables (use with caution!)"""
    with get_connection() as conn:
        # Drop trailing tables first (they have foreign keys)
        conn.execute(text("DROP TABLE IF EXISTS t_distractions"))
        conn.execute(text("DROP TABLE IF EXISTS t_selected_purposes"))
        conn.execute(text("DROP TABLE IF EXISTS t_selected_terrains"))
        conn.execute(text("DROP TABLE IF EXISTS t_training_sessions"))
        # Drop airscenting tables
        conn.execute(text("DROP TABLE IF EXISTS a_selected_purposes"))
        conn.execute(text("DROP TABLE IF EXISTS subject_responses"))
        conn.execute(text("DROP TABLE IF EXISTS selected_terrains"))
        conn.execute(text("DROP TABLE IF EXISTS training_sessions"))
        conn.execute(text("DROP TABLE IF EXISTS distraction_types"))
        conn.execute(text("DROP TABLE IF EXISTS terrain_types"))
        conn.execute(text("DROP TABLE IF EXISTS training_locations"))
        conn.execute(text("DROP TABLE IF EXISTS dogs"))
        conn.execute(text("DROP TABLE IF EXISTS settings"))
        conn.commit()
        print("All tables dropped")


if __name__ == "__main__":
    # Allow running this file directly to create tables
    create_tables()


def migrate_add_backup_columns():
    """
    Migration: Add entry_type, update_time, uuid, and status columns to training_sessions table.
    
    Safe to run multiple times - checks if columns exist before adding.
    Should be called at application startup to ensure schema is up to date.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    columns_to_add = [
        ("entry_type", "TEXT"),
        ("update_time", "TIMESTAMP"),
        ("uuid", "TEXT"),
        ("status", "TEXT DEFAULT 'active'"),
        ("checksum", "TEXT"),
        ("primary_timestamp", "TIMESTAMP"),
        ("secondary_timestamp", "TIMESTAMP")
    ]
    
    added_columns = []
    already_exists = []
    
    try:
        with get_connection() as conn:
            # Check which columns already exist
            if DB_TYPE == "sqlite":
                result = conn.execute(text("PRAGMA table_info(training_sessions)"))
                existing_columns = {row[1] for row in result.fetchall()}
            else:
                # PostgreSQL/MySQL - query information_schema
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'training_sessions'
                """))
                existing_columns = {row[0] for row in result.fetchall()}
            
            # Add missing columns
            for col_name, col_type in columns_to_add:
                if col_name in existing_columns:
                    already_exists.append(col_name)
                else:
                    # Add the column
                    alter_sql = f"ALTER TABLE training_sessions ADD COLUMN {col_name} {col_type}"
                    conn.execute(text(alter_sql))
                    added_columns.append(col_name)
            
            # Set existing rows to 'active' status if status column was just added
            if "status" in added_columns:
                conn.execute(text("UPDATE training_sessions SET status = 'active' WHERE status IS NULL"))
            
            conn.commit()
        
        # Build result message
        messages = []
        if added_columns:
            messages.append(f"Added columns: {', '.join(added_columns)}")
        if already_exists:
            messages.append(f"Already existed: {', '.join(already_exists)}")
        
        return True, "; ".join(messages) if messages else "No changes needed"
        
    except Exception as e:
        return False, f"Migration error: {e}"


def add_missing_columns_to_t_training_sessions():
    """
    Add missing columns to t_training_sessions table for backward compatibility.
    This allows older databases to work with newer code that expects these columns.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    columns_to_add = [
        ("entry_type", "TEXT"),
        ("update_time", "TIMESTAMP"),
        ("uuid", "TEXT"),
        ("status", "TEXT DEFAULT 'active'"),
        ("checksum", "TEXT"),
        ("primary_timestamp", "TIMESTAMP"),
        ("secondary_timestamp", "TIMESTAMP")
    ]
    
    added_columns = []
    already_exists = []
    
    try:
        with get_connection() as conn:
            # Check which columns already exist
            if DB_TYPE == "sqlite":
                result = conn.execute(text("PRAGMA table_info(t_training_sessions)"))
                existing_columns = {row[1] for row in result.fetchall()}
            else:
                # PostgreSQL/MySQL - query information_schema
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 't_training_sessions'
                """))
                existing_columns = {row[0] for row in result.fetchall()}
            
            # Add missing columns
            for col_name, col_type in columns_to_add:
                if col_name in existing_columns:
                    already_exists.append(col_name)
                else:
                    # Add the column
                    alter_sql = f"ALTER TABLE t_training_sessions ADD COLUMN {col_name} {col_type}"
                    conn.execute(text(alter_sql))
                    added_columns.append(col_name)
            
            # Set existing rows to 'active' status if status column was just added
            if "status" in added_columns:
                conn.execute(text("UPDATE t_training_sessions SET status = 'active' WHERE status IS NULL"))
            
            conn.commit()
        
        # Build result message
        messages = []
        if added_columns:
            messages.append(f"Added columns: {', '.join(added_columns)}")
        if already_exists:
            messages.append(f"Already existed: {', '.join(already_exists)}")
        
        return True, "; ".join(messages) if messages else "No changes needed"
        
    except Exception as e:
        return False, f"Migration error: {e}"


def migrate_add_a_selected_purposes_table():
    """
    Migration: Create a_selected_purposes table for airscenting session purposes.
    
    Safe to run multiple times - checks if table exists before creating.
    Should be called at application startup to ensure schema is up to date.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Auto-increment syntax differs between databases
        if DB_TYPE == "sqlite":
            id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        else:  # postgres or supabase
            id_type = "SERIAL PRIMARY KEY"
        
        with get_connection() as conn:
            # Check if table exists
            if DB_TYPE == "sqlite":
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='a_selected_purposes'"
                ))
            else:
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = 'a_selected_purposes'
                """))
            
            if result.fetchone():
                return True, "a_selected_purposes table already exists"
            
            # Create the table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS a_selected_purposes (
                    id {id_type},
                    session_id INTEGER NOT NULL,
                    purpose_name TEXT NOT NULL,
                    user_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES training_sessions(id)
                )
            """))
            conn.commit()
            
            return True, "Created a_selected_purposes table"
        
    except Exception as e:
        return False, f"Migration error: {e}"


def migrate_add_a_percent_searched_column():
    """
    Migration: Add a_percent_searched, start_time, and finish_time columns to training_sessions table.
    
    Safe to run multiple times - checks if columns exist before adding.
    Should be called at application startup to ensure schema is up to date.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    columns_to_add = [
        ('a_percent_searched', 'TEXT'),
        ('start_time', 'TEXT'),
        ('finish_time', 'TEXT')
    ]
    
    added_columns = []
    already_exists = []
    
    try:
        with get_connection() as conn:
            # Check which columns already exist
            if DB_TYPE == "sqlite":
                result = conn.execute(text("PRAGMA table_info(training_sessions)"))
                existing_columns = {row[1] for row in result.fetchall()}
            else:
                # PostgreSQL/MySQL - query information_schema
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'training_sessions'
                """))
                existing_columns = {row[0] for row in result.fetchall()}
            
            # Add missing columns
            for col_name, col_type in columns_to_add:
                if col_name in existing_columns:
                    already_exists.append(col_name)
                else:
                    # Add the column
                    alter_sql = f"ALTER TABLE training_sessions ADD COLUMN {col_name} {col_type}"
                    conn.execute(text(alter_sql))
                    added_columns.append(col_name)
            
            conn.commit()
            
            # Build result message
            messages = []
            if added_columns:
                messages.append(f"Added columns: {', '.join(added_columns)}")
            if already_exists:
                messages.append(f"Already existed: {', '.join(already_exists)}")
            
            return True, "; ".join(messages) if messages else "No changes needed"
        
    except Exception as e:
        return False, f"Migration error: {e}"


def migrate_add_cascade_delete():
    """
    Migration: Recreate foreign key tables with ON DELETE CASCADE.
    
    SQLite doesn't support ALTER TABLE to modify foreign keys, so we need to:
    1. Create new tables with proper CASCADE constraints
    2. Copy data from old tables
    3. Drop old tables
    4. Rename new tables
    
    This is safe to run multiple times - it checks if migration is needed.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    tables_to_migrate = [
        # (old_table, new_table_sql, parent_table, fk_column)
        ('selected_terrains', '''
            CREATE TABLE selected_terrains_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                terrain_name TEXT NOT NULL,
                user_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
            )
        ''', 'training_sessions', 'session_id'),
        ('subject_responses', '''
            CREATE TABLE subject_responses_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                subject_number INTEGER NOT NULL,
                tfr TEXT,
                refind TEXT,
                user_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
            )
        ''', 'training_sessions', 'session_id'),
        ('a_selected_purposes', '''
            CREATE TABLE a_selected_purposes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                purpose_name TEXT NOT NULL,
                user_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
            )
        ''', 'training_sessions', 'session_id'),
        ('t_selected_terrains', '''
            CREATE TABLE t_selected_terrains_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                t_session_id INTEGER NOT NULL,
                terrain_name TEXT NOT NULL,
                user_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (t_session_id) REFERENCES t_training_sessions(id) ON DELETE CASCADE
            )
        ''', 't_training_sessions', 't_session_id'),
        ('t_selected_purposes', '''
            CREATE TABLE t_selected_purposes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                t_session_id INTEGER NOT NULL,
                purpose_name TEXT NOT NULL,
                user_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (t_session_id) REFERENCES t_training_sessions(id) ON DELETE CASCADE
            )
        ''', 't_training_sessions', 't_session_id'),
        ('t_selected_distractions', '''
            CREATE TABLE t_selected_distractions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                t_session_id INTEGER NOT NULL,
                distraction_name TEXT NOT NULL,
                response TEXT,
                user_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (t_session_id) REFERENCES t_training_sessions(id) ON DELETE CASCADE
            )
        ''', 't_training_sessions', 't_session_id'),
    ]
    
    migrated = []
    skipped = []
    errors = []
    
    try:
        with get_connection() as conn:
            for old_table, new_table_sql, parent_table, fk_column in tables_to_migrate:
                try:
                    # Check if old table exists
                    result = conn.execute(text(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{old_table}'"
                    ))
                    if not result.fetchone():
                        skipped.append(f"{old_table} (not found)")
                        continue
                    
                    # Check if table already has CASCADE by looking at the schema
                    result = conn.execute(text(
                        f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{old_table}'"
                    ))
                    row = result.fetchone()
                    if row and 'ON DELETE CASCADE' in (row[0] or '').upper():
                        skipped.append(f"{old_table} (already has CASCADE)")
                        continue
                    
                    # Get columns from old table
                    result = conn.execute(text(f"PRAGMA table_info({old_table})"))
                    columns = [row[1] for row in result.fetchall()]
                    columns_str = ', '.join(columns)
                    
                    # Create new table with CASCADE
                    conn.execute(text(new_table_sql))
                    
                    # Copy data
                    conn.execute(text(f"INSERT INTO {old_table}_new ({columns_str}) SELECT {columns_str} FROM {old_table}"))
                    
                    # Drop old table
                    conn.execute(text(f"DROP TABLE {old_table}"))
                    
                    # Rename new table
                    conn.execute(text(f"ALTER TABLE {old_table}_new RENAME TO {old_table}"))
                    
                    migrated.append(old_table)
                    
                except Exception as e:
                    errors.append(f"{old_table}: {e}")
                    # Try to clean up new table if it exists
                    try:
                        conn.execute(text(f"DROP TABLE IF EXISTS {old_table}_new"))
                    except:
                        pass
            
            conn.commit()
        
        # Build result message
        messages = []
        if migrated:
            messages.append(f"Migrated: {', '.join(migrated)}")
        if skipped:
            messages.append(f"Skipped: {', '.join(skipped)}")
        if errors:
            messages.append(f"Errors: {', '.join(errors)}")
        
        return len(errors) == 0, "; ".join(messages) if messages else "No changes needed"
        
    except Exception as e:
        return False, f"Migration error: {e}"

