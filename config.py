"""
Configuration for Air-Scenting Logger
"""
import os
from pathlib import Path

# Database type - must be 'sqlite', 'postgres', 'supabase', or 'mysql'
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# Validate DB_TYPE
if DB_TYPE not in ["sqlite", "postgres", "supabase", "mysql"]:
    raise ValueError(f"Invalid DB_TYPE: '{DB_TYPE}'. Must be 'sqlite', 'postgres', 'supabase', or 'mysql'")

# Runtime password (set by UI, not stored in file)
DB_PASSWORD = None

# Database configuration
DB_CONFIG = {
    "sqlite": {
        "url": "sqlite:///air_scenting.db"
    },
    "postgres": {
        "url_template": "postgresql://user:{password}@localhost/air_scenting",
        "url": None  # Will be set at runtime with password
    },
    "supabase": {
        "url_template": "postgresql://postgres.hhsfivnljmmifmbuddba:{password}@aws-0-us-west-2.pooler.supabase.com:6543/postgres",
        "url": None  # Will be set at runtime with password
    },
    "mysql": {
        "url_template": "mysql+pymysql://user:{password}@localhost/air_scenting",
        "url": None  # Will be set at runtime with password
    }
}

# Application settings
APP_TITLE = "Air-Scenting Logger"
CONFIG_FILE = Path.home() / ".air_scenting_config.json"
BOOTSTRAP_FILE = Path.home() / ".airscent_bootstrap.json"
