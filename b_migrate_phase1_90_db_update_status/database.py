"""
Database connection management for Air-Scenting Logger
"""
from sqlalchemy import create_engine, text
import config  # Import module, not the variables

def get_db_url():
    """Get database URL, handling runtime password configuration"""
    if config.DB_TYPE == "sqlite":
        return config.DB_CONFIG["sqlite"]["url"]
    else:
        # For postgres, supabase, mysql - check if URL has been set at runtime
        url = config.DB_CONFIG[config.DB_TYPE].get("url")

        # print(f"DEBUG URL: {url}") # added by ahg
        # import traceback
        # print("DEBUG TRACEBACK:")
        # traceback.print_stack()
        # print("-" * 70)

        if url:
            return url
        else:
            # If not set, return template (will fail, but that's expected if password not provided)
            url_template = config.DB_CONFIG[config.DB_TYPE].get("url_template", "")
            # Return template with placeholder - this will cause an error if used
            return url_template.format(password="PASSWORD_NOT_SET")

# Create engine based on DB_TYPE
engine = create_engine(
    get_db_url(),
    echo=False,  # Set to True to see SQL queries for debugging
    # SQLite-specific: enable foreign keys (disabled by default)
    connect_args={"check_same_thread": False} if config.DB_TYPE == "sqlite" else {}
)

# Track if we've enabled foreign keys for SQLite
_sqlite_foreign_keys_enabled = False

def get_connection():
    """Get a new database connection"""
    global _sqlite_foreign_keys_enabled
    
    # Enable foreign keys for SQLite on first connection (creates DB file)
    if config.DB_TYPE == "sqlite" and not _sqlite_foreign_keys_enabled:
        conn = engine.connect()
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.commit()
        _sqlite_foreign_keys_enabled = True
        return conn
    
    return engine.connect()
