"""
Configuration for Trailing Logger
"""
import os
from pathlib import Path

# Database type - must be 'sqlite', 'postgres', 'supabase', or 'mysql'
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# Validate DB_TYPE
if DB_TYPE not in ["sqlite", "postgres", "supabase", "mysql"]:
    raise ValueError(f"Invalid DB_TYPE: '{DB_TYPE}'. Must be 'sqlite', 'postgres', 'supabase', or 'mysql'")

# Database password (set at runtime from encrypted storage)
DB_PASSWORD = None

# Database configuration
# For databases requiring passwords, use url_template with {password} placeholder
DB_CONFIG = {
    "sqlite": {
        "url": "sqlite:///air_scenting.db"
    },
    "postgres": {
        "url": os.getenv("DATABASE_URL", "postgresql://user:PASSWORD@localhost/air_scenting"),
        "url_template": "postgresql://user:{password}@localhost/air_scenting",
        "description": "PostgreSQL local database"
    },
    "supabase": {
        "url": "postgresql://postgres.hhsfivnljmmifmbuddba:PASSWORD@aws-0-us-west-2.pooler.supabase.com:6543/postgres",
        "url_template": "postgresql://postgres.hhsfivnljmmifmbuddba:{password}@aws-0-us-west-2.pooler.supabase.com:6543/postgres",
        "description": "Supabase cloud database"
    },
    "mysql": {
        "url": "mysql+pymysql://user:PASSWORD@localhost/air_scenting",
        "url_template": "mysql+pymysql://user:{password}@localhost/air_scenting",
        "description": "MySQL local database"
    }
}

# Application settings
APP_TITLE = "Trailing Logger"
CONFIG_FILE = Path.home() / ".training_log_config.json"  # Shared config file
BOOTSTRAP_FILE = Path.home() / ".training_log_bootstrap.json"  # Shared bootstrap file

# Trailing-specific constants
T_APP_TITLE = "Trailing Logger"
T_GITHUB_URL = "github.com/agelders2021/trailing_tracker"
