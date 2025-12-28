"""
Database connection management for Air-Scenting Logger
"""
from sqlalchemy import create_engine, text
from config import DB_TYPE, DB_CONFIG

# Create engine based on DB_TYPE
engine = create_engine(
    DB_CONFIG[DB_TYPE]["url"],
    echo=False,  # Set to True to see SQL queries for debugging
    # SQLite-specific: enable foreign keys (disabled by default)
    connect_args={"check_same_thread": False} if DB_TYPE == "sqlite" else {}
)

# Track if we've enabled foreign keys for SQLite
_sqlite_foreign_keys_enabled = False

def get_connection():
    """Get a new database connection"""
    global _sqlite_foreign_keys_enabled
    
    # Enable foreign keys for SQLite on first connection (creates DB file)
    if DB_TYPE == "sqlite" and not _sqlite_foreign_keys_enabled:
        conn = engine.connect()
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.commit()
        _sqlite_foreign_keys_enabled = True
        return conn
    
    return engine.connect()
