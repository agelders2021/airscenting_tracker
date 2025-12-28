"""
Configuration for Air-Scenting Logger
"""
import os
from pathlib import Path

# Database type - must be 'sqlite', 'postgres', or 'supabase'
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# Validate DB_TYPE
if DB_TYPE not in ["sqlite", "postgres", "supabase"]:
    raise ValueError(f"Invalid DB_TYPE: '{DB_TYPE}'. Must be 'sqlite', 'postgres', or 'supabase'")

# Database configuration
DB_CONFIG = {
    "sqlite": {
        "url": "sqlite:///air_scenting.db"
    },
    "postgres": {
        "url": os.getenv("DATABASE_URL", "postgresql://user:password@localhost/air_scenting")
    },
    "supabase": {
        "url": "postgresql://postgres.hhsfivnljmmifmbuddba:dvt1wkz1xek*UQE.wkb@aws-0-us-west-2.pooler.supabase.com:6543/postgres"
    }
}

# Application settings
APP_TITLE = "Air-Scenting Logger"
CONFIG_FILE = Path.home() / ".air_scenting_config.json"
BOOTSTRAP_FILE = Path.home() / ".airscent_bootstrap.json"
