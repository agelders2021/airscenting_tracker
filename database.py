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
Database connection management for Air-Scenting Logger

IMPORTANT: The engine is lazily initialized on first use. This allows the config
to be updated (e.g., from bootstrap) before any database operations occur.
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

# =============================================================================
# LAZY ENGINE INITIALIZATION
# The engine is NOT created at import time. Instead, it's created on first use.
# This allows config.DB_CONFIG to be updated (e.g., from bootstrap file) before
# any database operations occur.
# =============================================================================
_engine = None
_engine_url = None  # Track what URL the engine was created with

def _get_engine():
    """Get or create the database engine (lazy initialization)"""
    global _engine, _engine_url
    
    current_url = get_db_url()
    
    # Create engine if it doesn't exist OR if the URL has changed
    if _engine is None or _engine_url != current_url:
        if _engine is not None:
            _engine.dispose()
        
        _engine = create_engine(
            current_url,
            echo=False,  # Set to True to see SQL queries for debugging
            # SQLite-specific: enable foreign keys (disabled by default)
            connect_args={"check_same_thread": False} if config.DB_TYPE == "sqlite" else {}
        )
        _engine_url = current_url
    
    return _engine

# For backward compatibility, expose 'engine' as a property-like object
# Code that does 'from database import engine' will get this wrapper
class _EngineProxy:
    """Proxy object that forwards all attribute access to the lazily-created engine"""
    
    def __getattr__(self, name):
        return getattr(_get_engine(), name)
    
    def dispose(self):
        """Dispose the engine and reset for re-creation"""
        global _engine, _engine_url, _sqlite_foreign_keys_enabled
        if _engine is not None:
            _engine.dispose()
            _engine = None
            _engine_url = None
            _sqlite_foreign_keys_enabled = False

engine = _EngineProxy()

# Track if we've enabled foreign keys for SQLite
_sqlite_foreign_keys_enabled = False

def get_connection():
    """Get a new database connection"""
    global _sqlite_foreign_keys_enabled
    
    actual_engine = _get_engine()
    
    # Enable foreign keys for SQLite on first connection (creates DB file)
    if config.DB_TYPE == "sqlite" and not _sqlite_foreign_keys_enabled:
        conn = actual_engine.connect()
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.commit()
        _sqlite_foreign_keys_enabled = True
        return conn
    
    return actual_engine.connect()


def reinitialize_engine():
    """Force the engine to be recreated with current config.
    
    Call this after changing config.DB_CONFIG to ensure the engine
    uses the new settings.
    """
    global _engine, _engine_url, _sqlite_foreign_keys_enabled
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None
    _sqlite_foreign_keys_enabled = False
