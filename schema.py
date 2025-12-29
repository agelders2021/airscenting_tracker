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
    else:  # postgres or supabase
        dog_id_type = "SERIAL PRIMARY KEY"
        session_id_type = "SERIAL PRIMARY KEY"
        settings_id_type = "SERIAL PRIMARY KEY"
        location_id_type = "SERIAL PRIMARY KEY"
        terrain_id_type = "SERIAL PRIMARY KEY"
        distraction_id_type = "SERIAL PRIMARY KEY"
        selected_terrain_id_type = "SERIAL PRIMARY KEY"
        subject_response_id_type = "SERIAL PRIMARY KEY"
    
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
        comments TEXT,
        image_files TEXT,
        user_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        conn.commit()
        
        print("Database tables created successfully")


def drop_tables():
    """Drop all tables (use with caution!)"""
    with get_connection() as conn:
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
