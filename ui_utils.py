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
Utility Functions for Air-Scenting Logger
Helper functions used throughout the application
"""
import json
import shutil
from pathlib import Path
from getpass import getuser


def get_username():
    """Get the current system username"""
    try:
        return getuser()
    except:
        return "unknown"


def get_default_terrain_types():
    """Get the default terrain type list"""
    return [
        "Urban", "Rural", "Forest", "Scrub", "Desert", "Sandy", "Rocky", 
        "City park", "Meadow", "Dense brush", "Many cacti", "Stream", 
        "Roadway", "Marsh", "Mixed", "Industrial", "Residential"
    ]


def get_default_distraction_types():
    """Get the default distraction type list"""
    return [
        "Critter", "Horse", "Loud noise", "Motorcycle", "Hikers", 
        "Cow", "Vehicle"
    ]


def get_primary_json_folder():
    """Get the primary JSON folder path from sv.db_path"""
    import sv
    db_path = sv.db_path.get().strip()
    if db_path:
        json_folder = Path(db_path) / "JSON"
        if json_folder.exists():
            return json_folder
    return None


def get_primary_images_folder():
    """Get the primary Images folder path from sv.db_path"""
    import sv
    db_path = sv.db_path.get().strip()
    if db_path:
        images_folder = Path(db_path) / "Images"
        if images_folder.exists():
            return images_folder
    return None


def get_secondary_json_folder(create_if_missing=False):
    """Get the secondary JSON folder path from sv.backup_folder
    
    Args:
        create_if_missing: If True, create the folder if it doesn't exist
        
    Returns:
        Path to JSON folder, or None if backup_folder not configured
    """
    import sv
    backup_path = sv.backup_folder.get().strip()
    if backup_path:
        backup_root = Path(backup_path)
        if not backup_root.exists():
            print(f"get_secondary_json_folder: backup_root does not exist: {backup_root}")
            return None
        json_folder = backup_root / "JSON"
        if create_if_missing and not json_folder.exists():
            try:
                json_folder.mkdir(parents=True, exist_ok=True)
                print(f"Created secondary JSON folder: {json_folder}")
            except Exception as e:
                print(f"Warning: Could not create secondary JSON folder: {e}")
                return None
        if json_folder.exists():
            return json_folder
        else:
            print(f"get_secondary_json_folder: JSON folder does not exist: {json_folder}")
    else:
        print(f"get_secondary_json_folder: sv.backup_folder is empty")
    return None


def get_secondary_images_folder(create_if_missing=False):
    """Get the secondary Images folder path from sv.backup_folder
    
    Args:
        create_if_missing: If True, create the folder if it doesn't exist
        
    Returns:
        Path to Images folder, or None if backup_folder not configured
    """
    import sv
    backup_path = sv.backup_folder.get().strip()
    if backup_path:
        backup_root = Path(backup_path)
        if not backup_root.exists():
            return None
        images_folder = backup_root / "Images"
        if create_if_missing and not images_folder.exists():
            try:
                images_folder.mkdir(parents=True, exist_ok=True)
                print(f"Created secondary Images folder: {images_folder}")
            except Exception as e:
                print(f"Warning: Could not create secondary Images folder: {e}")
                return None
        if images_folder.exists():
            return images_folder
    return None


def save_json_mirrored(filename, data, indent=2):
    """
    Save JSON data to both primary and secondary JSON folders.
    Creates secondary JSON folder if it doesn't exist.
    
    Args:
        filename: Name of the JSON file (e.g., "a_Fido_1.json")
        data: Dictionary to save as JSON
        indent: JSON indentation (default 2)
        
    Returns:
        tuple: (primary_path, secondary_path, checksum, primary_ts, secondary_ts)
               - paths where files were saved (None if not saved)
               - SHA-256 checksum of data
               - file timestamps (datetime or None)
    """
    import hashlib
    from datetime import datetime
    
    primary_path = None
    secondary_path = None
    primary_ts = None
    secondary_ts = None
    
    # Compute checksum BEFORE saving (excludes checksum/timestamp fields from data)
    # Create a copy without internal tracking fields for consistent hashing
    data_for_hash = {k: v for k, v in data.items() 
                     if k not in ('checksum', 'primary_timestamp', 'secondary_timestamp')}
    json_str = json.dumps(data_for_hash, sort_keys=True, default=str)
    checksum = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    # Save to primary
    primary_folder = get_primary_json_folder()
    if primary_folder:
        primary_file = primary_folder / filename
        try:
            with open(primary_file, 'w') as f:
                json.dump(data, f, indent=indent, default=str)
            primary_path = primary_file
            primary_ts = datetime.fromtimestamp(primary_file.stat().st_mtime)
            print(f"Saved to primary: {primary_file}")
        except Exception as e:
            print(f"Warning: Failed to save to primary JSON folder: {e}")
    
    # Save to secondary (mirror) - create folder if needed
    secondary_folder = get_secondary_json_folder(create_if_missing=True)
    if secondary_folder:
        secondary_file = secondary_folder / filename
        try:
            with open(secondary_file, 'w') as f:
                json.dump(data, f, indent=indent, default=str)
            secondary_path = secondary_file
            secondary_ts = datetime.fromtimestamp(secondary_file.stat().st_mtime)
            print(f"Mirrored to secondary: {secondary_file}")
        except Exception as e:
            print(f"Warning: Failed to mirror to secondary JSON folder: {e}")
    
    return primary_path, secondary_path, checksum, primary_ts, secondary_ts


def copy_file_mirrored(source_path, filename):
    """
    Copy a file to both primary and secondary Images folders.
    Creates secondary Images folder if it doesn't exist.
    
    Args:
        source_path: Path to the source file to copy
        filename: Destination filename
        
    Returns:
        tuple: (primary_path, secondary_path) - paths where files were copied, None if not copied
    """
    source = Path(source_path)
    if not source.exists():
        print(f"Warning: Source file does not exist: {source_path}")
        return None, None
    
    primary_path = None
    secondary_path = None
    
    # Copy to primary
    primary_folder = get_primary_images_folder()
    if primary_folder:
        primary_file = primary_folder / filename
        try:
            shutil.copy2(str(source), str(primary_file))
            primary_path = primary_file
            print(f"Copied to primary: {primary_file}")
        except Exception as e:
            print(f"Warning: Failed to copy to primary Images folder: {e}")
    
    # Copy to secondary (mirror) - create folder if needed
    secondary_folder = get_secondary_images_folder(create_if_missing=True)
    if secondary_folder:
        secondary_file = secondary_folder / filename
        try:
            shutil.copy2(str(source), str(secondary_file))
            secondary_path = secondary_file
            print(f"Mirrored to secondary: {secondary_file}")
        except Exception as e:
            print(f"Warning: Failed to mirror to secondary Images folder: {e}")
    
    return primary_path, secondary_path


def delete_file_mirrored(filename, folder_type="json"):
    """
    Delete a file from both primary and secondary folders.
    
    Args:
        filename: Name of the file to delete
        folder_type: "json" or "images"
        
    Returns:
        tuple: (primary_deleted, secondary_deleted) - True if deleted, False otherwise
    """
    primary_deleted = False
    secondary_deleted = False
    
    if folder_type == "json":
        primary_folder = get_primary_json_folder()
        secondary_folder = get_secondary_json_folder()
    else:
        primary_folder = get_primary_images_folder()
        secondary_folder = get_secondary_images_folder()
    
    # Delete from primary
    if primary_folder:
        primary_file = primary_folder / filename
        if primary_file.exists():
            try:
                primary_file.unlink()
                primary_deleted = True
                print(f"Deleted from primary: {primary_file}")
            except Exception as e:
                print(f"Warning: Failed to delete from primary: {e}")
    
    # Delete from secondary
    if secondary_folder:
        secondary_file = secondary_folder / filename
        if secondary_file.exists():
            try:
                secondary_file.unlink()
                secondary_deleted = True
                print(f"Deleted from secondary: {secondary_file}")
            except Exception as e:
                print(f"Warning: Failed to delete from secondary: {e}")
    
    return primary_deleted, secondary_deleted
