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
Miscellaneous Data Operations for Air-Scenting Logger UI
Handles initialization, backups, restore, and default data loading
"""
import os
import json
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
from ui_utils import get_username, get_default_terrain_types, get_default_distraction_types
from ui_database import DatabaseOperations, get_db_manager
from working_dialog import WorkingDialog
import sv


class MiscDataOperations:
    """Handles miscellaneous data operations: initialization, backups, restore"""
    
    def __init__(self, ui):
        """Initialize with reference to main UI"""
        self.ui = ui
    
    def validate_database_at_startup(self):
        """
        Check if database exists and is valid at startup.
        If database is missing or corrupted, offer to rebuild from JSON backups.
        Also check if backup is newer than database and offer to restore.
        
        Returns:
            bool: True if database is valid or was successfully rebuilt, False otherwise
        """
        import config
        
        # Get the primary storage folder path
        db_folder = sv.db_path.get().strip()
        if not db_folder:
            # No folder configured - user needs to run setup
            return False
        
        folder_path = Path(db_folder)
        if not folder_path.exists():
            return False
        
        db_path = folder_path / "air_scenting.db"
        json_path = folder_path / "JSON"
        
        # Check if database exists
        if not db_path.exists():
            # Database missing - check for JSON backups
            return self._offer_rebuild_from_json(db_path, json_path, "Database file not found.")
        
        # Database file exists - check if it's valid using PRAGMA integrity_check
        try:
            import sqlite3
            
            # Use sqlite3 directly for integrity check (more reliable than SQLAlchemy for this)
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result[0] != "ok":
                # Database is corrupted
                conn.close()
                return self._offer_rebuild_from_json(db_path, json_path, 
                    f"Database integrity check failed: {result[0]}")
            
            # Also verify the schema exists (tables created)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='training_sessions'")
            table_exists = cursor.fetchone()
            conn.close()
            
            if not table_exists:
                return self._offer_rebuild_from_json(db_path, json_path, 
                    "Database is missing required tables.")
            
            # Database is valid - now set up SQLAlchemy to use it
            config.DB_TYPE = "sqlite"
            config.DB_CONFIG["sqlite"]["url"] = f"sqlite:///{db_path}"
            
            # Reload database engine
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            # Check if backup is newer than database
            self._check_backup_newer_than_db(db_path, json_path)
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            # print(f"Database validation error: {error_msg}")
            pass
            
            # Database exists but is corrupted or inaccessible
            return self._offer_rebuild_from_json(db_path, json_path, f"Database error: {error_msg}")
    
    def _check_backup_newer_than_db(self, db_path, json_path):
        """
        Check if the latest full backup file is newer than the last exit time.
        If so, offer to restore from the backup.
        
        Args:
            db_path: Path to database file
            json_path: Path to JSON backup folder
        """
        if not json_path.exists():
            return
        
        try:
            # Get last exit time from config (more reliable than DB mtime)
            last_exit_time = None
            if hasattr(self.ui, 'config') and self.ui.config:
                exit_time_str = self.ui.config.get("last_exit_time")
                if exit_time_str:
                    try:
                        last_exit_time = datetime.fromisoformat(exit_time_str)
                    except:
                        pass
            
            # If no exit time in config, fall back to database modification time
            if last_exit_time is None:
                last_exit_time = datetime.fromtimestamp(db_path.stat().st_mtime)
            
            # Find newest full backup file
            backup_files = list(json_path.glob("full_backup_*.json"))
            
            if not backup_files:
                return
            
            # Sort by modification time to find newest
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            newest_backup = backup_files[0]
            newest_mtime = datetime.fromtimestamp(newest_backup.stat().st_mtime)
            
            if newest_mtime > last_exit_time:
                # Backup is newer than last exit
                time_diff = newest_mtime - last_exit_time
                
                # Only alert if difference is more than a minute (to avoid false positives)
                if time_diff.total_seconds() > 60:
                    result = messagebox.askyesno(
                        "Newer Backup Found",
                        f"A backup file is newer than the last program exit:\n\n"
                        f"Last exit: {last_exit_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Backup created: {newest_mtime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Backup file: {newest_backup.name}\n\n"
                        f"This may indicate data was restored from another source.\n\n"
                        f"Would you like to restore from this backup?",
                        icon='warning'
                    )
                    
                    if result:
                        self._restore_from_full_backup(newest_backup)
        except Exception as e:
            # Don't block startup on check errors
            pass
    
    def _restore_from_full_backup(self, backup_file):
        """Restore entire database from a full backup JSON file."""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Verify it's a full backup file
            if backup_data.get("backup_version") != "2.0":
                messagebox.showerror("Invalid Backup", "This does not appear to be a valid full backup file.")
                return False
            
            result = self._perform_full_restore(backup_data)
            
            if result:
                messagebox.showinfo("Restore Complete", 
                    f"Database restored from backup:\n{backup_file.name}")
            
            return result
            
        except Exception as e:
            messagebox.showerror("Restore Error", f"Failed to restore from backup:\n{e}")
            return False
    
    def _check_secondary_for_newer_backup(self):
        """
        Check if the secondary backup folder has a newer full_backup file
        than the primary folder.  If so, analyse the backup to identify
        exactly which sessions differ, present the details to the user,
        and merge only if the user confirms.

        Called once during startup, after the database has been validated.
        """
        try:
            secondary_folder = sv.backup_folder.get().strip()
            if not secondary_folder:
                return

            secondary_path = Path(secondary_folder)
            if not secondary_path.exists():
                return

            secondary_json = secondary_path / "JSON"
            if not secondary_json.exists():
                return

            # Find newest full backup in secondary
            sec_backups = list(secondary_json.glob("full_backup_*.json"))
            if not sec_backups:
                return

            sec_backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            newest_secondary = sec_backups[0]
            sec_mtime = datetime.fromtimestamp(newest_secondary.stat().st_mtime)

            # Find newest full backup in primary
            primary_folder = sv.db_path.get().strip()
            if not primary_folder:
                return

            primary_json = Path(primary_folder) / "JSON"
            pri_mtime = datetime.min  # default if no primary backups exist

            if primary_json.exists():
                pri_backups = list(primary_json.glob("full_backup_*.json"))
                if pri_backups:
                    pri_backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    pri_mtime = datetime.fromtimestamp(pri_backups[0].stat().st_mtime)

            # Compare: secondary must be newer by more than 60 seconds
            if sec_mtime <= pri_mtime or (sec_mtime - pri_mtime).total_seconds() <= 60:
                return

            # --- Load the backup and analyse changes -----------------------
            try:
                with open(newest_secondary, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            except Exception:
                return

            if backup_data.get("backup_version") != "2.0":
                return

            changes = self._analyze_secondary_backup_changes(backup_data)

            if not changes:
                return  # analysis failed

            air_updated  = changes.get("air_updated", [])
            air_added    = changes.get("air_added", [])
            trail_updated = changes.get("trail_updated", [])
            trail_added  = changes.get("trail_added", [])

            total = len(air_updated) + len(air_added) + len(trail_updated) + len(trail_added)
            if total == 0:
                return  # nothing to do

            # --- Build a detailed message for the user ---------------------
            msg = (
                f"The secondary backup folder contains a more recent "
                f"backup than the primary folder:\n\n"
                f"Secondary backup: {newest_secondary.name}\n"
                f"  Created: {sec_mtime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Primary latest: "
                f"{pri_mtime.strftime('%Y-%m-%d %H:%M:%S') if pri_mtime != datetime.min else '(none)'}"
                f"\n\n"
            )

            if air_added:
                msg += f"New Area Search sessions ({len(air_added)}):\n"
                for desc in air_added:
                    msg += f"  + {desc}\n"
                msg += "\n"

            if air_updated:
                msg += f"Updated Area Search sessions ({len(air_updated)}):\n"
                for desc in air_updated:
                    msg += f"  * {desc}\n"
                msg += "\n"

            if trail_added:
                msg += f"New Trailing sessions ({len(trail_added)}):\n"
                for desc in trail_added:
                    msg += f"  + {desc}\n"
                msg += "\n"

            if trail_updated:
                msg += f"Updated Trailing sessions ({len(trail_updated)}):\n"
                for desc in trail_updated:
                    msg += f"  * {desc}\n"
                msg += "\n"

            msg += "Would you like to apply these changes?"

            result = messagebox.askyesno(
                "Newer Secondary Backup Found", msg, icon='question')

            if result:
                self._merge_secondary_backup_sessions(backup_data)

        except Exception:
            # Never block startup on this check
            pass

    def _parse_update_time_value(self, value):
        """
        Parse an update_time value to a datetime for comparison.
        Handles datetime objects, ISO strings (with T or space separator),
        and None/empty.

        Returns:
            datetime or None
        """
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Normalise common formats
            cleaned = value.replace('T', ' ').rstrip('Z').split('+')[0].strip()
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(cleaned, fmt)
                except ValueError:
                    continue
        return None

    def _analyze_secondary_backup_changes(self, backup_data):
        """
        Read-only comparison of *backup_data* against the current database.
        Returns a dict with four lists of human-readable descriptions:

            {
                "air_updated":   ["Dog Fido #3 (2026-01-15)", ...],
                "air_added":     [...],
                "trail_updated": [...],
                "trail_added":   [...],
            }

        Returns None on error.
        """
        from sqlalchemy import text as sa_text

        try:
            result = {
                "air_updated": [],
                "air_added": [],
                "trail_updated": [],
                "trail_added": [],
            }

            # --- Airscenting sessions --------------------------------------
            for bk in backup_data.get("airscenting_sessions", []):
                try:
                    snum = bk.get("session_number")
                    dog  = bk.get("dog_name")
                    if snum is None or not dog:
                        continue

                    bk_time = self._parse_update_time_value(bk.get("update_time"))
                    bk_date = bk.get("date", "")
                    desc = f"Dog {dog} #{snum}"
                    if bk_date:
                        desc += f" ({bk_date})"

                    from database import get_connection
                    with get_connection() as conn:
                        row = conn.execute(
                            sa_text("SELECT id, update_time FROM training_sessions "
                                    "WHERE session_number = :snum AND dog_name = :dog"),
                            {"snum": snum, "dog": dog}
                        ).fetchone()

                    if row:
                        db_time = self._parse_update_time_value(row[1])
                        if bk_time and (db_time is None or bk_time > db_time):
                            result["air_updated"].append(desc)
                    else:
                        result["air_added"].append(desc)
                except Exception:
                    pass

            # --- Trailing sessions -----------------------------------------
            for bk in backup_data.get("trailing_sessions", []):
                try:
                    snum = bk.get("t_session_number")
                    dog  = bk.get("t_dog_name")
                    if snum is None or not dog:
                        continue

                    bk_time = self._parse_update_time_value(bk.get("update_time"))
                    bk_date = bk.get("t_date", "")
                    desc = f"Dog {dog} #{snum}"
                    if bk_date:
                        desc += f" ({bk_date})"

                    from database import get_connection
                    with get_connection() as conn:
                        row = conn.execute(
                            sa_text("SELECT id, update_time FROM t_training_sessions "
                                    "WHERE t_session_number = :snum "
                                    "AND t_dog_name = :dog"),
                            {"snum": snum, "dog": dog}
                        ).fetchone()

                    if row:
                        db_time = self._parse_update_time_value(row[1])
                        if bk_time and (db_time is None or bk_time > db_time):
                            result["trail_updated"].append(desc)
                    else:
                        result["trail_added"].append(desc)
                except Exception:
                    pass

            return result

        except Exception:
            return None

    def _merge_secondary_backup_sessions(self, backup_data):
        """
        Merge individual sessions from *backup_data* into the database,
        updating only those whose update_time is newer than what is in the
        DB and inserting any that are entirely new.

        Also updates child-table rows (terrains, purposes, responses,
        distractions) for every session that is touched.

        Args:
            backup_data: Already-loaded dict from a full_backup_*.json file
        """
        from sqlalchemy import text as sa_text
        import database
        from importlib import reload

        try:
            # --- set up database connection --------------------------------
            import config
            old_db_type = config.DB_TYPE
            db_type = sv.db_type.get()
            config.DB_TYPE = db_type

            from database import engine
            engine.dispose()
            reload(database)

            stats = {
                "air_updated": 0,
                "air_added": 0,
                "trail_updated": 0,
                "trail_added": 0,
            }

            # ---------------------------------------------------------------
            # Build lookup indexes for child-table rows in the backup.
            # Key = backup session id  Ã¢â€ â€™  list of child rows
            # ---------------------------------------------------------------
            air_child_tables = {
                "selected_terrains": {},       # session_id Ã¢â€ â€™ [rows]
                "a_selected_purposes": {},     # session_id Ã¢â€ â€™ [rows]
                "subject_responses": {},       # session_id Ã¢â€ â€™ [rows]
            }
            trail_child_tables = {
                "t_selected_terrains": {},     # t_session_id Ã¢â€ â€™ [rows]
                "t_selected_purposes": {},     # t_session_id Ã¢â€ â€™ [rows]
                "t_distractions": {},          # t_session_id Ã¢â€ â€™ [rows]
            }

            for table_key, idx_dict in air_child_tables.items():
                for row in backup_data.get(table_key, []):
                    sid = row.get("session_id")
                    if sid is not None:
                        idx_dict.setdefault(sid, []).append(row)

            for table_key, idx_dict in trail_child_tables.items():
                for row in backup_data.get(table_key, []):
                    sid = row.get("t_session_id")
                    if sid is not None:
                        idx_dict.setdefault(sid, []).append(row)

            # ---------------------------------------------------------------
            # Airscenting sessions
            # ---------------------------------------------------------------
            for bk_session in backup_data.get("airscenting_sessions", []):
                try:
                    snum = bk_session.get("session_number")
                    dog  = bk_session.get("dog_name")
                    if snum is None or not dog:
                        continue

                    bk_time = self._parse_update_time_value(
                        bk_session.get("update_time"))

                    with database.get_connection() as conn:
                        row = conn.execute(
                            sa_text("SELECT id, update_time FROM training_sessions "
                                    "WHERE session_number = :snum AND dog_name = :dog"),
                            {"snum": snum, "dog": dog}
                        ).fetchone()

                        if row:
                            db_id = row[0]
                            db_time = self._parse_update_time_value(row[1])

                            # Only update if backup is strictly newer
                            if bk_time and (db_time is None or bk_time > db_time):
                                # Update main session row
                                cols = [k for k in bk_session.keys()
                                        if k not in ('id',)]
                                set_clause = ', '.join(
                                    [f"{c} = :{c}" for c in cols])
                                params = {c: bk_session.get(c) for c in cols}
                                params["_db_id"] = db_id
                                conn.execute(
                                    sa_text(f"UPDATE training_sessions "
                                            f"SET {set_clause} WHERE id = :_db_id"),
                                    params)

                                # Replace child rows
                                self._replace_air_child_rows(
                                    conn, db_id,
                                    bk_session.get("id"),
                                    air_child_tables)

                                conn.commit()
                                stats["air_updated"] += 1
                        else:
                            # New session Ã¢â‚¬â€œ insert
                            bk_id = bk_session.get("id")
                            cols = [k for k in bk_session.keys()
                                    if k not in ('id',)]
                            placeholders = [f":{c}" for c in cols]
                            params = {c: bk_session.get(c) for c in cols}
                            conn.execute(
                                sa_text(f"INSERT INTO training_sessions "
                                        f"({', '.join(cols)}) "
                                        f"VALUES ({', '.join(placeholders)})"),
                                params)

                            # Retrieve the new id
                            new_row = conn.execute(
                                sa_text("SELECT id FROM training_sessions "
                                        "WHERE session_number = :snum "
                                        "AND dog_name = :dog"),
                                {"snum": snum, "dog": dog}
                            ).fetchone()
                            if new_row:
                                self._replace_air_child_rows(
                                    conn, new_row[0], bk_id,
                                    air_child_tables)

                            conn.commit()
                            stats["air_added"] += 1

                except Exception:
                    pass  # skip problematic sessions

            # ---------------------------------------------------------------
            # Trailing sessions
            # ---------------------------------------------------------------
            for bk_session in backup_data.get("trailing_sessions", []):
                try:
                    snum = bk_session.get("t_session_number")
                    dog  = bk_session.get("t_dog_name")
                    if snum is None or not dog:
                        continue

                    bk_time = self._parse_update_time_value(
                        bk_session.get("update_time"))

                    with database.get_connection() as conn:
                        row = conn.execute(
                            sa_text("SELECT id, update_time FROM t_training_sessions "
                                    "WHERE t_session_number = :snum "
                                    "AND t_dog_name = :dog"),
                            {"snum": snum, "dog": dog}
                        ).fetchone()

                        if row:
                            db_id = row[0]
                            db_time = self._parse_update_time_value(row[1])

                            if bk_time and (db_time is None or bk_time > db_time):
                                cols = [k for k in bk_session.keys()
                                        if k not in ('id',)]
                                set_clause = ', '.join(
                                    [f"{c} = :{c}" for c in cols])
                                params = {c: bk_session.get(c) for c in cols}
                                params["_db_id"] = db_id
                                conn.execute(
                                    sa_text(f"UPDATE t_training_sessions "
                                            f"SET {set_clause} WHERE id = :_db_id"),
                                    params)

                                self._replace_trail_child_rows(
                                    conn, db_id,
                                    bk_session.get("id"),
                                    trail_child_tables)

                                conn.commit()
                                stats["trail_updated"] += 1
                        else:
                            bk_id = bk_session.get("id")
                            cols = [k for k in bk_session.keys()
                                    if k not in ('id',)]
                            placeholders = [f":{c}" for c in cols]
                            params = {c: bk_session.get(c) for c in cols}
                            conn.execute(
                                sa_text(f"INSERT INTO t_training_sessions "
                                        f"({', '.join(cols)}) "
                                        f"VALUES ({', '.join(placeholders)})"),
                                params)

                            new_row = conn.execute(
                                sa_text("SELECT id FROM t_training_sessions "
                                        "WHERE t_session_number = :snum "
                                        "AND t_dog_name = :dog"),
                                {"snum": snum, "dog": dog}
                            ).fetchone()
                            if new_row:
                                self._replace_trail_child_rows(
                                    conn, new_row[0], bk_id,
                                    trail_child_tables)

                            conn.commit()
                            stats["trail_added"] += 1

                except Exception:
                    pass

            # --- ensure dog names from backup exist in dogs table ----------
            # Sessions may reference dogs not yet in the local dogs table.
            # Only dog names matter here; other setup lists are less critical.
            if stats["air_added"] or stats["trail_added"] or stats["air_updated"] or stats["trail_updated"]:
                try:
                    from ui_utils import get_username
                    for bk_dog in backup_data.get("dogs", []):
                        dog_name = bk_dog.get("name")
                        if not dog_name:
                            continue
                        with database.get_connection() as conn:
                            exists = conn.execute(
                                sa_text("SELECT id FROM dogs WHERE name = :name"),
                                {"name": dog_name}
                            ).fetchone()
                            if not exists:
                                conn.execute(
                                    sa_text("INSERT INTO dogs (name, user_name) "
                                            "VALUES (:name, :user_name)"),
                                    {"name": dog_name,
                                     "user_name": bk_dog.get("user_name", get_username())})
                                conn.commit()
                                stats["dogs_added"] = stats.get("dogs_added", 0) + 1
                except Exception:
                    pass  # non-fatal; sessions are already merged

            # --- restore original DB type ----------------------------------
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)

            # --- summary ---------------------------------------------------
            total = sum(stats.values())

            # --- refresh UI if anything changed ----------------------------
            if total > 0:
                self._refresh_ui_after_secondary_merge()

            if total > 0:
                msg = "Secondary backup merge complete!\n\n"
                if stats.get("dogs_added"):
                    msg += f"  Added {stats['dogs_added']} dog name(s)\n"
                if stats["air_added"]:
                    msg += f"  Added {stats['air_added']} Area Search session(s)\n"
                if stats["air_updated"]:
                    msg += f"  Updated {stats['air_updated']} Area Search session(s)\n"
                if stats["trail_added"]:
                    msg += f"  Added {stats['trail_added']} Trailing session(s)\n"
                if stats["trail_updated"]:
                    msg += f"  Updated {stats['trail_updated']} Trailing session(s)\n"
                messagebox.showinfo("Merge Complete", msg)
            else:
                messagebox.showinfo(
                    "Merge Complete",
                    "All sessions in the secondary backup are already "
                    "up-to-date in the database.")

        except Exception as e:
            # Restore DB type on error
            try:
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except Exception:
                pass
            messagebox.showerror("Merge Error",
                                 f"Failed to merge from secondary backup:\n{e}")

    # ------------------------------------------------------------------
    # UI refresh after secondary merge
    # ------------------------------------------------------------------

    def _refresh_ui_after_secondary_merge(self):
        """
        Refresh all relevant UI elements after sessions have been merged
        from a secondary backup.  This covers both the Area Search and
        Trailing tabs so that session numbers, navigation buttons, and
        combo-box lists are up-to-date.
        """
        try:
            # --- Refresh setup-tab lists and entry-tab combo boxes ---------
            self.ui.load_dogs_from_database()
            self.ui.load_locations_from_database()
            self.ui.load_terrain_from_database()
            self.ui.load_distraction_from_database()

            if hasattr(self.ui, 'a_dog_combo'):
                self.ui.refresh_dog_list()
            if hasattr(self.ui, 'a_location_combo'):
                self.ui.refresh_location_list()
            if hasattr(self.ui, 'a_terrain_combo'):
                self.ui.refresh_terrain_list()
            if hasattr(self.ui, 'trailing_entry'):
                self.ui.refresh_distraction_list()

            # --- Area Search session number --------------------------------
            current_dog = sv.dog.get()
            if current_dog:
                try:
                    db_ops = DatabaseOperations(self.ui)
                    status_filter = sv.session_status_filter.get()
                    filtered = db_ops.get_all_sessions_for_dog(
                        current_dog, status_filter, entry_type="Airscent")
                    next_num = len(filtered) + 1
                    sv.session_number.set(str(next_num))
                except Exception:
                    pass

            # --- Area Search navigation buttons ----------------------------
            if hasattr(self.ui, 'navigation'):
                try:
                    self.ui.navigation.update_navigation_buttons()
                except Exception:
                    pass

            # --- Trailing session number -----------------------------------
            trailing_dog = sv.t_dog.get() if hasattr(sv, 't_dog') else ""
            if trailing_dog and hasattr(self.ui, 'trailing_entry'):
                try:
                    next_t = self.ui.get_trailing_next_session_number(trailing_dog)
                    sv.t_session.set(str(next_t))
                except Exception:
                    pass

            # --- Trailing navigation buttons -------------------------------
            if hasattr(self.ui, 'trailing_entry'):
                try:
                    self.ui._update_trailing_navigation_buttons()
                except Exception:
                    pass

            # --- Re-snapshot forms so merge changes are not flagged as
            #     unsaved edits ------------------------------------------
            if hasattr(self.ui, 'form_mgmt'):
                try:
                    self.ui.form_mgmt.take_form_snapshot()
                except Exception:
                    pass
            if hasattr(self.ui, 'trailing_entry') and hasattr(
                    self.ui.trailing_entry, 'take_form_snapshot'):
                try:
                    self.ui.trailing_entry.take_form_snapshot()
                except Exception:
                    pass

        except Exception:
            pass  # Never block startup

    # ------------------------------------------------------------------
    # Child-table replacement helpers
    # ------------------------------------------------------------------

    def _replace_air_child_rows(self, conn, db_session_id, bk_session_id,
                                child_index):
        """
        Delete existing child rows for *db_session_id* and re-insert
        from the backup index keyed by *bk_session_id*.

        Args:
            conn: open database connection (caller manages commit)
            db_session_id: the ``id`` in the local DB
            bk_session_id: the ``id`` from the backup file (may be None)
            child_index: dict of {table_key: {bk_session_id: [rows]}}
        """
        from sqlalchemy import text as sa_text

        if bk_session_id is None:
            return

        # Delete existing child rows for this session
        for db_table in ("selected_terrains", "a_selected_purposes",
                         "subject_responses"):
            conn.execute(
                sa_text(f"DELETE FROM {db_table} WHERE session_id = :sid"),
                {"sid": db_session_id})

        # Insert backup child rows with the correct local session_id
        for table_key in ("selected_terrains", "a_selected_purposes",
                          "subject_responses"):
            for row in child_index.get(table_key, {}).get(bk_session_id, []):
                cols = [k for k in row.keys() if k not in ('id', 'session_id')]
                if not cols:
                    continue
                col_names = ['session_id'] + cols
                placeholders = [':session_id'] + [f':{c}' for c in cols]
                params = {c: row.get(c) for c in cols}
                params['session_id'] = db_session_id
                conn.execute(
                    sa_text(f"INSERT INTO {table_key} "
                            f"({', '.join(col_names)}) "
                            f"VALUES ({', '.join(placeholders)})"),
                    params)

    def _replace_trail_child_rows(self, conn, db_session_id, bk_session_id,
                                  child_index):
        """
        Delete existing child rows for *db_session_id* and re-insert
        from the backup index keyed by *bk_session_id*.

        Args:
            conn: open database connection (caller manages commit)
            db_session_id: the ``id`` in the local DB
            bk_session_id: the ``id`` from the backup file (may be None)
            child_index: dict of {table_key: {bk_session_id: [rows]}}
        """
        from sqlalchemy import text as sa_text

        if bk_session_id is None:
            return

        for db_table in ("t_selected_terrains", "t_selected_purposes",
                         "t_distractions"):
            conn.execute(
                sa_text(f"DELETE FROM {db_table} WHERE t_session_id = :sid"),
                {"sid": db_session_id})

        for table_key in ("t_selected_terrains", "t_selected_purposes",
                          "t_distractions"):
            for row in child_index.get(table_key, {}).get(bk_session_id, []):
                cols = [k for k in row.keys()
                        if k not in ('id', 't_session_id')]
                if not cols:
                    continue
                col_names = ['t_session_id'] + cols
                placeholders = [':t_session_id'] + [f':{c}' for c in cols]
                params = {c: row.get(c) for c in cols}
                params['t_session_id'] = db_session_id
                conn.execute(
                    sa_text(f"INSERT INTO {table_key} "
                            f"({', '.join(col_names)}) "
                            f"VALUES ({', '.join(placeholders)})"),
                    params)

    def _offer_rebuild_from_json(self, db_path, json_path, reason):
        """
        Offer to rebuild database from JSON backup files.
        Shows a selection dialog for full backup files.
        
        Args:
            db_path: Path to database file
            json_path: Path to JSON backup folder
            reason: Reason why rebuild is needed
            
        Returns:
            bool: True if database was rebuilt successfully, False otherwise
        """
        # Check if JSON backup folder exists
        if not json_path.exists():
            messagebox.showwarning(
                "No Database",
                f"{reason}\n\n"
                f"No JSON backup folder found at:\n{json_path}\n\n"
                "Please use Setup tab to initialize data structures."
            )
            return False
        
        # Look for full backup files first (new format)
        full_backup_files = list(json_path.glob("full_backup_*.json"))
        
        # Also check for legacy individual session files
        legacy_session_files = list(json_path.glob("*session_*.json"))
        legacy_session_files += list(json_path.glob("a_*.json"))
        legacy_session_files += list(json_path.glob("t_*.json"))
        
        config_file = json_path / ".training_log_config.json"
        has_config = config_file.exists()
        
        if not full_backup_files and not legacy_session_files and not has_config:
            messagebox.showwarning(
                "No Database",
                f"{reason}\n\n"
                f"No backup files found in:\n{json_path}\n\n"
                "Please use Setup tab to initialize data structures."
            )
            return False
        
        # If we have full backup files, show selection dialog
        if full_backup_files:
            result = messagebox.askyesno(
                "Rebuild Database?",
                f"{reason}\n\n"
                f"Found {len(full_backup_files)} full backup file(s) in:\n{json_path}\n\n"
                "Would you like to select a backup to restore from?",
                icon='question'
            )
            
            if not result:
                return False
            
            # Create database first, then show selection dialog
            if not self._create_empty_database(db_path):
                return False
            
            # Show backup selection dialog
            return self._show_startup_backup_selection(full_backup_files, db_path)
        
        # Fall back to legacy restore if no full backups
        restore_items = []
        if legacy_session_files:
            restore_items.append(f"{len(legacy_session_files)} session backup file(s)")
        if has_config:
            restore_items.append("configuration data (dogs, terrains, locations)")
        
        result = messagebox.askyesno(
            "Rebuild Database?",
            f"{reason}\n\n"
            f"Found in {json_path}:\n" + "\n".join(f"  • {item}" for item in restore_items) + "\n\n"
            "Would you like to rebuild the database from these backups?",
            icon='question'
        )
        
        if not result:
            return False
        
        # Create database and restore from legacy files
        if not self._create_empty_database(db_path):
            return False
        
        sv.show_status_message("Database recreated, restoring from backups...", "info")
        self._restore_sessions_from_json(json_path)
        return True
    
    def _create_empty_database(self, db_path):
        """Create a new empty database with schema. Returns True on success."""
        try:
            # Delete corrupted database if it exists
            if db_path.exists():
                try:
                    from database import engine
                    engine.dispose()
                    import gc
                    gc.collect()
                    import time
                    time.sleep(0.5)
                    db_path.unlink()
                    # Also delete WAL files
                    wal_file = Path(str(db_path) + "-wal")
                    shm_file = Path(str(db_path) + "-shm")
                    if wal_file.exists():
                        wal_file.unlink()
                    if shm_file.exists():
                        shm_file.unlink()
                except Exception as e:
                    messagebox.showerror("Error", f"Could not remove corrupted database:\n{e}")
                    return False
            
            # Create new database
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.close()
            
            # Update config
            import config
            config.DB_TYPE = "sqlite"
            config.DB_CONFIG["sqlite"]["url"] = f"sqlite:///{db_path}"
            
            # Reload database engine
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            # Create schema
            from schema import create_tables
            create_tables()
            
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create database:\n{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _show_startup_backup_selection(self, backup_files, db_path):
        """Show backup selection dialog at startup when database is missing."""
        import tkinter as tk
        
        # Create a temporary root if needed (during startup)
        temp_root = None
        if not hasattr(self.ui, 'root') or self.ui.root is None:
            temp_root = tk.Tk()
            temp_root.withdraw()
            parent = temp_root
        else:
            parent = self.ui.root
        
        dialog = tk.Toplevel(parent)
        dialog.title("Select Backup to Restore")
        dialog.geometry("600x400")
        dialog.resizable(True, True)
        dialog.transient(parent)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width // 2) - (dialog.winfo_width() // 2)
        y = (screen_height // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Result variable
        selected_file = [None]
        
        # Header
        header = tk.Label(dialog, text="Database needs to be restored.\nSelect a backup file:", 
                         font=("Helvetica", 11, "bold"), justify="center")
        header.pack(pady=10)
        
        # Listbox with backup files
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, selectmode="single", yscrollcommand=scrollbar.set,
                            font=("Courier", 10), height=12)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Sort files by modification time (newest first) and collect info
        file_info = []
        for f in backup_files:
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                size_kb = f.stat().st_size / 1024
                
                # Try to read session counts from file
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                    air_count = len(data.get("airscenting_sessions", []))
                    trail_count = len(data.get("trailing_sessions", []))
                    info_str = f"  ({air_count} air, {trail_count} trail)"
                except:
                    info_str = ""
                
                file_info.append((f, mtime, size_kb, info_str))
            except:
                file_info.append((f, datetime.min, 0, ""))
        
        file_info.sort(key=lambda x: x[1], reverse=True)
        
        for f, mtime, size_kb, info_str in file_info:
            display = f"{mtime.strftime('%Y-%m-%d %H:%M')}  {size_kb:8.1f} KB{info_str}"
            listbox.insert(tk.END, display)
        
        # Select newest by default
        if file_info:
            listbox.select_set(0)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def do_restore():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a backup file to restore")
                return
            selected_file[0] = file_info[selection[0]][0]
            dialog.destroy()
        
        def do_cancel():
            dialog.destroy()
        
        tk.Button(button_frame, text="Restore Selected", command=do_restore, 
                 bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=do_cancel, width=10).pack(side=tk.LEFT, padx=5)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        # Clean up temp root if created
        if temp_root:
            temp_root.destroy()
        
        # Perform restore if file was selected
        if selected_file[0]:
            return self._restore_from_full_backup(selected_file[0])
        
        return False
    
    def _restore_sessions_from_json(self, json_path):
        """
        Restore sessions from JSON backup files (internal helper, no prompts).
        Also restores config data if available.
        
        Args:
            json_path: Path to JSON backup folder
        """
        import database
        
        json_files = list(json_path.glob("*session_*.json"))
        
        restored_count = 0
        failed_count = 0
        dog_names = set()
        location_names = set()
        
        # Restore sessions if any exist
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r') as f:
                    session_data = json.load(f)
                
                # Collect dog name
                dog_name = session_data.get('dog_name')
                if dog_name:
                    dog_names.add(dog_name)
                
                # Collect location name
                location = session_data.get('location')
                if location:
                    location_names.add(location)
                
                # Insert into database
                with database.get_connection() as conn:
                    image_files = session_data.get('image_files', [])
                    image_files_json = json.dumps(image_files) if isinstance(image_files, list) else (image_files or "")
                    
                    conn.execute(
                        text("""
                            INSERT INTO training_sessions 
                            (date, session_number, handler, session_purpose, field_support, dog_name, location,
                             search_area_size, num_subjects, handler_knowledge, weather, temperature, 
                             wind_direction, wind_speed, search_type, drive_level, subjects_found, 
                             comments, image_files, user_name)
                            VALUES (:date, :session_number, :handler, :session_purpose, :field_support, :dog_name, :location,
                                    :search_area_size, :num_subjects, :handler_knowledge, :weather, :temperature, 
                                    :wind_direction, :wind_speed, :search_type, :drive_level, :subjects_found,
                                    :comments, :image_files, :user_name)
                        """),
                        {
                            "date": session_data.get('date'),
                            "session_number": session_data.get('session_number'),
                            "handler": session_data.get('handler'),
                            "session_purpose": session_data.get('session_purpose'),
                            "field_support": session_data.get('field_support'),
                            "dog_name": session_data.get('dog_name'),
                            "location": session_data.get('location'),
                            "search_area_size": session_data.get('search_area_size'),
                            "num_subjects": session_data.get('num_subjects'),
                            "handler_knowledge": session_data.get('handler_knowledge'),
                            "weather": session_data.get('weather'),
                            "temperature": session_data.get('temperature'),
                            "wind_direction": session_data.get('wind_direction'),
                            "wind_speed": session_data.get('wind_speed'),
                            "search_type": session_data.get('search_type'),
                            "drive_level": session_data.get('drive_level'),
                            "subjects_found": session_data.get('subjects_found'),
                            "comments": session_data.get('comments'),
                            "image_files": image_files_json,
                            "user_name": session_data.get('user_name', get_username())
                        }
                    )
                    conn.commit()
                
                restored_count += 1
                
            except Exception as e:
                # print(f"Failed to restore {json_file}: {e}")
                failed_count += 1
        
        # Add dog names to database
        for dog_name in sorted(dog_names):
            try:
                with database.get_connection() as conn:
                    conn.execute(
                        text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                        {"name": dog_name, "user_name": get_username()}
                    )
                    conn.commit()
            except:
                pass  # Duplicate OK
        
        # Add location names to database
        for location in sorted(location_names):
            try:
                with database.get_connection() as conn:
                    conn.execute(
                        text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                        {"name": location, "user_name": get_username()}
                    )
                    conn.commit()
            except:
                pass  # Duplicate OK
        
        # Also restore from config file if it exists
        config_restored = self._restore_config_data_to_db(json_path)
        
        sv.show_status_message(f"Restored {restored_count} session(s) from backup", "info")
        if restored_count > 0 or config_restored:
            msg = f"Successfully restored {restored_count} session(s) from JSON backups."
            if config_restored:
                msg += "\n\nAlso restored configuration data (dogs, terrains, locations, distractions)."
            if failed_count > 0:
                msg += f"\n\n{failed_count} file(s) failed to restore."
            messagebox.showinfo("Database Rebuilt", msg)
    
    def _restore_config_data_to_db(self, json_path):
        """
        Restore configuration data (dogs, terrains, locations, distractions) from config file.
        
        Args:
            json_path: Path to JSON folder containing .training_log_config.json
            
        Returns:
            bool: True if config was restored, False otherwise
        """
        import database
        
        config_file = json_path / ".training_log_config.json"
        if not config_file.exists():
            return False
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except Exception as e:
            # print(f"Could not load config file: {e}")
            return False
        
        restored_something = False
        
        # Restore dog names
        dog_names = config_data.get("dog_names", [])
        for dog_name in dog_names:
            if dog_name:
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                            {"name": dog_name, "user_name": get_username()}
                        )
                        conn.commit()
                    restored_something = True
                except:
                    pass  # Duplicate OK
        
        # Restore terrain types
        terrain_types = config_data.get("terrain_types", [])
        for i, terrain in enumerate(terrain_types):
            if terrain:
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO terrain_types (name, sort_order, user_name) VALUES (:name, :sort_order, :user_name)"),
                            {"name": terrain, "sort_order": i, "user_name": get_username()}
                        )
                        conn.commit()
                    restored_something = True
                except:
                    pass  # Duplicate OK
        
        # Restore distraction types
        distraction_types = config_data.get("distraction_types", [])
        for i, distraction in enumerate(distraction_types):
            if distraction:
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO distraction_types (name, sort_order, user_name) VALUES (:name, :sort_order, :user_name)"),
                            {"name": distraction, "sort_order": i, "user_name": get_username()}
                        )
                        conn.commit()
                    restored_something = True
                except:
                    pass  # Duplicate OK
        
        # Restore training locations
        locations = config_data.get("training_locations", [])
        for location in locations:
            if location:
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                            {"name": location, "user_name": get_username()}
                        )
                        conn.commit()
                    restored_something = True
                except:
                    pass  # Duplicate OK
        
        return restored_something

    def load_initial_database_data(self):
        """Load all initial database data after splash screen starts"""
        # Use chained after() calls to let event loop run between operations
        # This keeps splash countdown and progress bars animating
        
        # Disable View/Edit/Hide and Export PDF buttons until startup is complete
        self._disable_sync_sensitive_buttons()
        
        def step0():
            # First validate the database exists and is valid
            # This will offer to rebuild from JSON if needed
            if not self.validate_database_at_startup():
                # Database not valid and couldn't be rebuilt
                # Skip loading data, user needs to set up
                sv.show_status_message("Database not configured - please complete Setup", "warning")
                self._enable_sync_sensitive_buttons()  # Re-enable since we're done
                return
            
            # Check if secondary backup folder has a newer backup than primary
            self._check_secondary_for_newer_backup()
            
            # Check if database is healthy before deciding sync strategy
            db_healthy = self._check_db_health()
            
            if db_healthy:
                # DB is healthy - start sync in background thread
                self._start_startup_sync_thread()
            else:
                # DB appears damaged - run sync synchronously to rebuild
                # print("Database appears damaged - running synchronous rebuild...")
                self._perform_synchronous_startup_sync()
                self._enable_sync_sensitive_buttons()
            
            self.ui.root.after(50, step1)
        
        def step1():
            self.ensure_db_ready()
            self.ui.load_locations_from_database()
            self.ui.root.after(50, step2)  # Schedule next step
        
        def step2():
            self.ui.load_dogs_from_database()
            self.ui.root.after(50, step3)
        
        def step3():
            self.ui.load_terrain_from_database()
            self.ui.root.after(50, step4)
        
        def step4():
            self.ui.load_distraction_from_database()
            self.ui.root.after(50, step5)
        
        def step5():
            # Load last selected dog from database
            try:
                last_dog = DatabaseOperations(self.ui).load_db_setting("last_dog_name", "")
                if last_dog:
                    sv.dog.set(last_dog)
                    # Update session number for this dog (on_dog_changed not triggered by programmatic set)
                    # Use computed next number based on filter (Airscent sessions only)
                    status_filter = sv.session_status_filter.get()
                    filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(
                        last_dog, status_filter, entry_type="Airscent"
                    )
                    next_computed = len(filtered_sessions) + 1
                    sv.session_number.set(str(next_computed))
            except Exception as e:
                # print(f"Could not load last dog: {e}")
                pass
            self.ui.root.after(50, step6)
        
        def step6():
            # Refresh Entry tab comboboxes if they exist
            if hasattr(self.ui, 'a_dog_combo'):
                self.ui.refresh_dog_list()
            self.ui.root.after(50, step7)
        
        def step7():
            if hasattr(self.ui, 'a_location_combo'):
                self.ui.refresh_location_list()
            self.ui.root.after(50, step8)
        
        def step8():
            if hasattr(self.ui, 'a_terrain_combo'):
                self.ui.refresh_terrain_list()
            self.ui.root.after(50, step9)
        
        def step9():
            # Update navigation buttons now that dog and session are loaded
            if hasattr(self.ui, 'a_prev_session_btn'):
                self.ui.navigation.update_navigation_buttons()
            self.ui.root.after(100, step10)
        
        def step10():
            # Sync was already started in step0
            # Buttons will be re-enabled when sync thread completes
            
            # Select Entry tab since database is valid
            # (We only get here if validate_database_at_startup returned True)
            if hasattr(self.ui, 'notebook') and hasattr(self.ui, 'entry_tab'):
                self.ui.notebook.select(self.ui.entry_tab)
                # print("Database valid - starting on Entry tab")
                pass
        
        # Start the chain with database validation
        step0()
    
    def _disable_sync_sensitive_buttons(self):
        """Disable buttons that shouldn't be used during sync."""
        import tkinter as tk
        sv.sync_in_progress = True
        if hasattr(self.ui, 'a_edit_delete_btn'):
            self.ui.a_edit_delete_btn.config(state=tk.DISABLED)
        if hasattr(self.ui, 'a_export_pdf_btn'):
            self.ui.a_export_pdf_btn.config(state=tk.DISABLED)
    
    def _enable_sync_sensitive_buttons(self):
        """Re-enable buttons after sync completes."""
        import tkinter as tk
        sv.sync_in_progress = False
        if hasattr(self.ui, 'a_edit_delete_btn'):
            self.ui.a_edit_delete_btn.config(state=tk.NORMAL)
        if hasattr(self.ui, 'a_export_pdf_btn'):
            self.ui.a_export_pdf_btn.config(state=tk.NORMAL)
    
    def _check_db_health(self) -> bool:
        """Check if database is accessible and has required tables."""
        try:
            from sqlalchemy import text
            from database import get_connection
            with get_connection() as conn:
                conn.execute(text("SELECT COUNT(*) FROM training_sessions"))
                conn.execute(text("SELECT COUNT(*) FROM t_training_sessions"))
            return True
        except Exception as e:
            # print(f"Database health check failed: {e}")
            return False
    
    def _start_startup_sync_thread(self):
        """Start startup sync in a background thread."""
        import threading
        from ui_utils import get_primary_json_folder, get_secondary_json_folder
        
        db_type = sv.db_type.get()
        primary_folder = get_primary_json_folder()
        secondary_folder = get_secondary_json_folder()
        
        if not primary_folder:
            # print("Startup sync: No primary JSON folder configured, skipping")
            self._enable_sync_sensitive_buttons()
            return
        
        def do_sync():
            """Run sync in background thread"""
            try:
                from backup_sync import BackupSyncManager
                
                sync_manager = BackupSyncManager(
                    db_type=db_type,
                    primary_folder=primary_folder,
                    secondary_folder=secondary_folder
                )
                
                def status_callback(message):
                    def update():
                        sv.show_status_message(message, "info")
                    self.ui.root.after(0, update)
                
                results = sync_manager.perform_full_sync(status_callback=status_callback)
                
                def on_complete():
                    # Re-enable buttons
                    self._enable_sync_sensitive_buttons()
                    
                    # Update session number if DB was updated
                    db_updates = results.get('db_updates', 0)
                    if db_updates > 0:
                        dog_name = sv.dog.get()
                        if dog_name:
                            try:
                                from ui_database import DatabaseOperations
                                status_filter = sv.session_status_filter.get()
                                filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(
                                    dog_name, status_filter, entry_type="Airscent"
                                )
                                next_computed = len(filtered_sessions) + 1
                                sv.session_number.set(str(next_computed))
                                # print(f"Startup sync: Updated session number to {next_computed} for {dog_name}")
                                pass
                            except Exception as e:
                                pass  # Error updating session number
                    
                    # Update status
                    total_changes = (
                        db_updates +
                        results.get('primary_writes', 0) +
                        results.get('secondary_writes', 0) +
                        results.get('renames', 0)
                    )
                    
                    if total_changes > 0:
                        sv.show_status_message(f"Sync complete: {total_changes} file(s) synchronized", "info")
                    else:
                        sv.show_status_message("Ready", "info")
                
                self.ui.root.after(0, on_complete)
                
            except Exception as e:
                # print(f"Startup sync error: {e}")
                import traceback
                traceback.print_exc()
                
                def reset():
                    self._enable_sync_sensitive_buttons()
                    sv.show_status_message("Ready", "info")
                self.ui.root.after(0, reset)
        
        # Start sync thread
        sync_thread = threading.Thread(target=do_sync, daemon=True)
        sync_thread.start()
        # print("Startup sync: Started in background thread")
        pass
    
    def _perform_synchronous_startup_sync(self):
        """Perform startup sync synchronously (blocking) for DB rebuild."""
        try:
            from backup_sync import BackupSyncManager
            from ui_utils import get_primary_json_folder, get_secondary_json_folder
            
            db_type = sv.db_type.get()
            primary_folder = get_primary_json_folder()
            secondary_folder = get_secondary_json_folder()
            
            if not primary_folder:
                # print("Startup sync: No primary JSON folder configured, skipping")
                return
            
            # print("Startup sync: Beginning synchronous synchronization...")
            sv.show_status_message("Rebuilding database from backups...", "info")
            self.ui.root.update_idletasks()
            
            sync_manager = BackupSyncManager(
                db_type=db_type,
                primary_folder=primary_folder,
                secondary_folder=secondary_folder
            )
            
            def status_callback(message):
                # print(f"  {message}")
                sv.show_status_message(message, "info")
                self.ui.root.update_idletasks()
            
            results = sync_manager.perform_full_sync(status_callback=status_callback)
            
            total_changes = (
                results.get('db_updates', 0) +
                results.get('primary_writes', 0) +
                results.get('secondary_writes', 0) +
                results.get('renames', 0)
            )
            
            if total_changes > 0:
                # print(f"Startup sync complete: {total_changes} change(s)")
                sv.show_status_message(f"Rebuild complete: {total_changes} file(s) synchronized", "info")
            else:
                # print("Startup sync complete: All backups already in sync")
                sv.show_status_message("Ready", "info")
            
        except Exception as e:
            # print(f"Startup sync error: {e}")
            import traceback
            traceback.print_exc()
    
    def _start_background_sync(self):
        """Start background sync between database and JSON backup folders.
        
        Uses the new backup_sync module for comprehensive synchronization
        with checksum tracking and proper conflict resolution.
        
        Note: Buttons are already disabled by load_initial_database_data.
        This method will re-enable them when sync completes.
        """
        import threading
        from ui_utils import get_primary_json_folder, get_secondary_json_folder
        
        try:
            db_type = sv.db_type.get()
            primary_folder = get_primary_json_folder()
            secondary_folder = get_secondary_json_folder()
            
            if not primary_folder:
                # print("Sync: No primary JSON folder configured, skipping sync")
                self._enable_sync_sensitive_buttons()
                return
            
            def do_sync():
                """Run sync in background thread"""
                try:
                    from backup_sync import BackupSyncManager
                    
                    sync_manager = BackupSyncManager(
                        db_type=db_type,
                        primary_folder=primary_folder,
                        secondary_folder=secondary_folder
                    )
                    
                    def status_callback(message):
                        def update():
                            sv.show_status_message(message, "info")
                        self.ui.root.after(0, update)
                    
                    results = sync_manager.perform_full_sync(status_callback=status_callback)
                    
                    def update_ui():
                        # Re-enable buttons
                        self._enable_sync_sensitive_buttons()
                        
                        # Update session number if sessions were added
                        db_updates = results.get("db_updates", 0)
                        if db_updates > 0:
                            # Recalculate session number for current dog
                            dog_name = sv.dog.get()
                            if dog_name:
                                try:
                                    from ui_database import DatabaseOperations
                                    status_filter = sv.session_status_filter.get()
                                    filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(
                                        dog_name, status_filter, entry_type="Airscent"
                                    )
                                    next_computed = len(filtered_sessions) + 1
                                    sv.session_number.set(str(next_computed))
                                    # print(f"Sync: Updated session number to {next_computed} for {dog_name}")
                                    pass
                                except Exception as e:
                                    # print(f"Sync: Error updating session number: {e}")
                                    pass
                        
                        # Build status message
                        total_changes = (
                            db_updates +
                            results.get('primary_writes', 0) +
                            results.get('secondary_writes', 0) +
                            results.get('renames', 0)
                        )
                        
                        if total_changes > 0:
                            sv.show_status_message(f"Sync complete: {total_changes} file(s) synchronized", "info")
                        else:
                            sv.show_status_message("Sync complete: All backups up to date", "info")
                        
                        if results.get('errors'):
                            # print(f"Sync errors: {results['errors']}")
                            pass
                        
                        # Export sessions to Excel after sync
                        self._export_sessions_to_excel_after_sync()
                    
                    self.ui.root.after(0, update_ui)
                    
                except Exception as e:
                    # print(f"Background sync error: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    def reset_ui():
                        self._enable_sync_sensitive_buttons()
                    self.ui.root.after(0, reset_ui)
            
            # Start sync thread
            sync_thread = threading.Thread(target=do_sync, daemon=True)
            sync_thread.start()
            
            # print("Sync: Background sync started")
            pass
            
        except Exception as e:
            # print(f"Error starting background sync: {e}")
            self._enable_sync_sensitive_buttons()
    
    def select_initial_tab(self):
        """Select initial tab based on database existence"""
        db_type = sv.db_type.get()
        database_exists = False
        
        # Check if database exists
        if db_type == "sqlite":
            # For SQLite, check if database file exists
            import config as config_module
            db_path = config_module.DB_CONFIG["sqlite"]["url"].replace("sqlite:///", "")
            if os.path.exists(db_path):
                # Check if it has tables (not just an empty file)
                try:
                    import config
                    old_db_type = config.DB_TYPE
                    config.DB_TYPE = db_type
                    
                    from database import engine
                    engine.dispose()
                    from importlib import reload
                    import database
                    reload(database)
                    
                    # Try to query a table
                    with database.get_connection() as conn:
                        conn.execute(text("SELECT COUNT(*) FROM training_sessions"))
                    
                    database_exists = True
                    
                    # Restore original DB_TYPE
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except:
                    # If query fails, database doesn't have proper tables
                    try:
                        import config
                        import database
                        from importlib import reload
                        config.DB_TYPE = old_db_type
                        database.engine.dispose()
                        reload(database)
                    except:
                        pass
                    database_exists = False
        else:
            # For PostgreSQL/Supabase, try to connect and query
            try:
                import config
                old_db_type = config.DB_TYPE
                config.DB_TYPE = db_type
                
                from database import engine
                engine.dispose()
                from importlib import reload
                import database
                reload(database)
                
                # Try to query a table
                with database.get_connection() as conn:
                    conn.execute(text("SELECT COUNT(*) FROM training_sessions"))
                
                database_exists = True
                
                # Restore original DB_TYPE
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                # If connection or query fails, database doesn't exist
                try:
                    import config
                    import database
                    from importlib import reload
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    reload(database)
                except:
                    pass
                database_exists = False
        
        # Select appropriate tab
        if database_exists:
            # Database exists - show Training Session Entry tab
            self.ui.notebook.select(self.ui.entry_tab)
            self.ui.previous_tab_index = 1  # Update to reflect we're on Entry tab
        else:
            # No database - show Setup tab (already default)
            self.ui.notebook.select(self.ui.setup_tab)
            self.ui.previous_tab_index = 0
    
    # def save_session_to_json(self, session_data):
    #     """Save session data to JSON backup file in both primary and secondary locations.
        
    #     Uses consistent naming: a_{user}_{dog}_{session_number}.json
    #     Updates database with checksum and file timestamps.
    #     """
    #     import re
    #     from ui_utils import save_json_mirrored, get_secondary_json_folder
        
    #     try:
    #         # Get session info for filename (session_number from DB, not calculated)
    #         session_num = session_data.get('session_number')
    #         dog_name = session_data.get('dog_name', 'unknown')
    #         user_name = session_data.get('user_name', '')
            
    #         # Sanitize names for filename (remove special characters)
    #         safe_user_name = re.sub(r'[^\w\-]', '_', user_name) if user_name else 'unknown'
    #         safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
            
    #         # Consistent naming convention: a_{user}_{dog}_{session}.json
    #         filename = f"a_{safe_user_name}_{safe_dog_name}_{session_num}.json"
            
    #         # Add timestamp to data
    #         session_data['update_time'] = datetime.now().isoformat()
            
    #         # Save to both primary and secondary (returns checksum and timestamps)
    #         primary, secondary, checksum, primary_ts, secondary_ts = save_json_mirrored(filename, session_data)
            
    #         if primary:
    #             # print(f"Session backup saved: {primary}")
    #             pass
    #         if secondary:
    #             # print(f"Session backup mirrored: {secondary}")
    #             pass
            
    #         # Update database with checksum and timestamps
    #         if checksum:
    #             try:
    #                 self._update_session_backup_info(session_num, dog_name, checksum, primary_ts, secondary_ts)
    #             except Exception as e:
    #                 # print(f"Warning: Could not update backup info in DB: {e}")
    #                 pass
            
    #         # Check if secondary backup was configured but unavailable
    #         # Notify user once per session via status bar
    #         if not secondary and sv.backup_folder.get().strip():
    #             if not sv.secondary_unavailable_notified:
    #                 sv.secondary_unavailable_notified = True
    #                 sv.show_status_message("Warning: Secondary backup folder unavailable - backup saved to primary only", "warning")
                    
    #     except Exception as e:
    #         error_msg = f"Backup failed: {str(e)}"
    #         # print(f"Warning: Failed to save session to JSON: {e}")
    #         self.ui.show_status_message(error_msg, "error")
    
    def _update_session_backup_info(self, session_number, dog_name, checksum, primary_ts, secondary_ts):
        """Update checksum and timestamps in database for a session."""
        try:
            from sqlalchemy import text
            from database import get_connection
            
            with get_connection() as conn:
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
                    'session_number': session_number,
                    'dog_name': dog_name
                })
                conn.commit()
                # print(f"Updated backup info: checksum={checksum[:16]}..., primary_ts={primary_ts}, secondary_ts={secondary_ts}")
                pass
        except Exception as e:
            # print(f"Error updating session backup info: {e}")
            pass
    
    def save_settings_backup(self):
        """Save settings to JSON backup file in both primary and secondary locations.
        
        Uses the main config file which is already mirrored to secondary.
        """
        try:
            # The main config file already contains all settings and is mirrored
            # Just ensure config is up-to-date and save it
            self.ui.save_config()
            # print("Settings backup saved via main config file")
            pass
        except Exception as e:
            # print(f"Warning: Failed to save settings backup: {e}")
            pass
    
    def _export_sessions_to_excel_after_sync(self):
        """
        Export sessions to Excel files after sync completion.
        Only exports when a dedicated Excel folder has been configured in Setup.
        """
        try:
            excel_folder = sv.excel_folder.get().strip()
            
            # Only export when a dedicated Excel folder has been configured
            if not excel_folder:
                return
            
            from backup_management import export_all_sessions_to_excel
            
            db_type = sv.db_type.get()
            
            success, msg = export_all_sessions_to_excel(
                db_type, 
                excel_folder,
                None  # No secondary for dedicated Excel folder
            )
            
            if success:
                # print(f"Excel export: {msg}")
                pass
            else:
                # print(f"Excel export failed: {msg}")
                pass
                
        except Exception as e:
            # print(f"Error exporting sessions to Excel: {e}")
            import traceback
            traceback.print_exc()
    
    def restore_settings_from_json(self):
        """Restore from secondary backup folder - show selection dialog for full backup files."""
        # Block if sync is in progress
        if sv.sync_in_progress:
            messagebox.showinfo(
                "Sync In Progress",
                "Please wait - background sync is in progress.\n\n"
                "Restore operations are temporarily disabled to ensure data integrity."
            )
            return
        
        backup_folder = sv.backup_folder.get().strip()
        if not backup_folder:
            messagebox.showwarning("No Backup Folder", "Please select a secondary backup folder first")
            return
        
        backup_path = Path(backup_folder)
        if not backup_path.exists():
            messagebox.showwarning("Invalid Folder", f"Secondary backup folder does not exist:\n{backup_folder}")
            return
        
        # Look for JSON subfolder
        json_subfolder = backup_path / "JSON"
        if not json_subfolder.exists():
            messagebox.showinfo("No Backups", f"No JSON backup folder found in:\n{backup_folder}")
            return
        
        # Find full backup files
        backup_files = list(json_subfolder.glob("full_backup_*.json"))
        
        if not backup_files:
            messagebox.showinfo("No Backups", f"No full backup files found in:\n{json_subfolder}\n\nLooking for: full_backup_*.json")
            return
        
        # Show selection dialog
        self._show_backup_selection_dialog(backup_files)
    
    def _show_backup_selection_dialog(self, backup_files):
        """Show dialog for selecting which backup file to restore."""
        import tkinter as tk
        from tkinter import ttk
        
        dialog = tk.Toplevel(self.ui.root)
        dialog.title("Restore from Backup")
        dialog.geometry("600x400")
        dialog.resizable(True, True)
        dialog.transient(self.ui.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.ui.root.winfo_x() + (self.ui.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.ui.root.winfo_y() + (self.ui.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Header
        header = tk.Label(dialog, text="Select a backup file to restore:", font=("Helvetica", 11, "bold"))
        header.pack(pady=10)
        
        # Warning
        warning = tk.Label(dialog, 
            text="⚠️ Warning: Restoring will add missing data from the backup.\nExisting data will not be overwritten.",
            fg="orange", justify="center")
        warning.pack(pady=5)
        
        # Listbox with backup files
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, selectmode="single", yscrollcommand=scrollbar.set,
                            font=("Courier", 10), height=12)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Sort files by modification time (newest first) and collect info
        file_info = []
        for f in backup_files:
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                size_kb = f.stat().st_size / 1024
                
                # Try to read session counts from file
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                    air_count = len(data.get("airscenting_sessions", []))
                    trail_count = len(data.get("trailing_sessions", []))
                    info_str = f"  ({air_count} air, {trail_count} trail)"
                except:
                    info_str = ""
                
                file_info.append((f, mtime, size_kb, info_str))
            except:
                file_info.append((f, datetime.min, 0, ""))
        
        file_info.sort(key=lambda x: x[1], reverse=True)
        
        for f, mtime, size_kb, info_str in file_info:
            display = f"{mtime.strftime('%Y-%m-%d %H:%M')}  {size_kb:8.1f} KB{info_str}"
            listbox.insert(tk.END, display)
        
        # Select newest by default
        if file_info:
            listbox.select_set(0)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def do_restore():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a backup file to restore")
                return
            
            selected_file = file_info[selection[0]][0]
            dialog.destroy()
            
            # Confirm restore
            result = messagebox.askyesno(
                "Confirm Restore",
                f"Are you sure you want to restore from:\n\n{selected_file.name}\n\n"
                "This will add any missing data to the current database.",
                icon='question'
            )
            
            if result:
                self._restore_from_full_backup(selected_file)
        
        tk.Button(button_frame, text="Restore Selected", command=do_restore, 
                 bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
    
    def _perform_full_restore(self, backup_data):
        """Perform a full restore from backup data dictionary."""
        import database
        from importlib import reload
        
        db_type = sv.db_type.get()
        
        # Set up database connection
        import config
        old_db_type = config.DB_TYPE
        config.DB_TYPE = db_type
        
        from database import engine
        engine.dispose()
        reload(database)
        
        stats = {
            "dogs_added": 0,
            "locations_added": 0,
            "terrain_added": 0,
            "distraction_added": 0,
            "air_sessions_added": 0,
            "trail_sessions_added": 0
        }
        
        try:
            # Restore dogs
            for dog in backup_data.get("dogs", []):
                try:
                    with database.get_connection() as conn:
                        check = conn.execute(text("SELECT id FROM dogs WHERE name = :name"),
                                           {"name": dog.get("name")}).fetchone()
                        if not check:
                            conn.execute(text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                                       {"name": dog.get("name"), "user_name": dog.get("user_name", get_username())})
                            conn.commit()
                            stats["dogs_added"] += 1
                except:
                    pass
            
            # Restore locations
            for loc in backup_data.get("locations", []):
                try:
                    with database.get_connection() as conn:
                        check = conn.execute(text("SELECT id FROM training_locations WHERE name = :name"),
                                           {"name": loc.get("name")}).fetchone()
                        if not check:
                            conn.execute(text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                                       {"name": loc.get("name"), "user_name": loc.get("user_name", get_username())})
                            conn.commit()
                            stats["locations_added"] += 1
                except:
                    pass
            
            # Restore terrain types
            for terrain in backup_data.get("terrain_types", []):
                try:
                    with database.get_connection() as conn:
                        check = conn.execute(text("SELECT id FROM terrain_types WHERE name = :name"),
                                           {"name": terrain.get("name")}).fetchone()
                        if not check:
                            conn.execute(text("INSERT INTO terrain_types (name, user_name, sort_order) VALUES (:name, :user_name, :sort_order)"),
                                       {"name": terrain.get("name"), "user_name": terrain.get("user_name", get_username()),
                                        "sort_order": terrain.get("sort_order", 0)})
                            conn.commit()
                            stats["terrain_added"] += 1
                except:
                    pass
            
            # Restore distraction types
            for distraction in backup_data.get("distraction_types", []):
                try:
                    with database.get_connection() as conn:
                        check = conn.execute(text("SELECT id FROM distraction_types WHERE name = :name"),
                                           {"name": distraction.get("name")}).fetchone()
                        if not check:
                            conn.execute(text("INSERT INTO distraction_types (name, user_name, sort_order) VALUES (:name, :user_name, :sort_order)"),
                                       {"name": distraction.get("name"), "user_name": distraction.get("user_name", get_username()),
                                        "sort_order": distraction.get("sort_order", 0)})
                            conn.commit()
                            stats["distraction_added"] += 1
                except:
                    pass
            
            # Restore airscenting sessions
            for session in backup_data.get("airscenting_sessions", []):
                try:
                    with database.get_connection() as conn:
                        # Check if session exists
                        check = conn.execute(
                            text("SELECT id FROM training_sessions WHERE session_number = :num AND dog_name = :dog"),
                            {"num": session.get("session_number"), "dog": session.get("dog_name")}
                        ).fetchone()
                        
                        if not check:
                            # Build insert - use column names from backup
                            columns = [k for k in session.keys() if k != 'id']
                            placeholders = [f":{k}" for k in columns]
                            
                            sql = f"INSERT INTO training_sessions ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                            params = {k: session.get(k) for k in columns}
                            
                            conn.execute(text(sql), params)
                            conn.commit()
                            stats["air_sessions_added"] += 1
                except:
                    pass
            
            # Restore trailing sessions
            for session in backup_data.get("trailing_sessions", []):
                try:
                    with database.get_connection() as conn:
                        # Check if session exists
                        check = conn.execute(
                            text("SELECT id FROM t_training_sessions WHERE t_session_number = :num AND t_dog_name = :dog"),
                            {"num": session.get("t_session_number"), "dog": session.get("t_dog_name")}
                        ).fetchone()
                        
                        if not check:
                            # Build insert - use column names from backup
                            columns = [k for k in session.keys() if k != 'id']
                            placeholders = [f":{k}" for k in columns]
                            
                            sql = f"INSERT INTO t_training_sessions ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                            params = {k: session.get(k) for k in columns}
                            
                            conn.execute(text(sql), params)
                            conn.commit()
                            stats["trail_sessions_added"] += 1
                except:
                    pass
            
            # Restore related tables if present
            self._restore_related_tables(backup_data, database)
            
            # Restore config settings from backup (excluding window geometry)
            backup_config = backup_data.get("config", {})
            if backup_config and hasattr(self.ui, 'config'):
                # Keys to exclude from restore - window geometry is machine-specific
                exclude_keys = {"window_geometry"}
                
                for key, value in backup_config.items():
                    if key in exclude_keys:
                        continue
                    if isinstance(value, dict):
                        # For nested sections (airscenting, trailing), merge
                        # but still exclude window_geometry inside them
                        if key not in self.ui.config:
                            self.ui.config[key] = {}
                        for subkey, subvalue in value.items():
                            if subkey in exclude_keys:
                                continue
                            self.ui.config[key][subkey] = subvalue
                    else:
                        self.ui.config[key] = value
                
                self.ui.save_config()
                stats["config_restored"] = True
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Refresh UI
            self.ui.load_dogs_from_database()
            if hasattr(self.ui, 'a_dog_combo'):
                self.ui.refresh_dog_list()
            
            self.ui.load_locations_from_database()
            if hasattr(self.ui, 'a_location_combo'):
                self.ui.refresh_location_list()
            
            self.ui.load_terrain_from_database()
            self.ui.load_distraction_from_database()
            if hasattr(self.ui, 'a_terrain_combo'):
                self.ui.refresh_terrain_list()
            
            # Show summary
            total = sum(v for v in stats.values() if isinstance(v, int))
            config_restored = stats.get("config_restored", False)
            if total > 0 or config_restored:
                msg = "Restore complete!\n\n"
                if stats["dogs_added"] > 0:
                    msg += f"Added {stats['dogs_added']} dog(s)\n"
                if stats["locations_added"] > 0:
                    msg += f"Added {stats['locations_added']} location(s)\n"
                if stats["terrain_added"] > 0:
                    msg += f"Added {stats['terrain_added']} terrain type(s)\n"
                if stats["distraction_added"] > 0:
                    msg += f"Added {stats['distraction_added']} distraction type(s)\n"
                if stats["air_sessions_added"] > 0:
                    msg += f"Added {stats['air_sessions_added']} airscenting session(s)\n"
                if stats["trail_sessions_added"] > 0:
                    msg += f"Added {stats['trail_sessions_added']} trailing session(s)\n"
                if config_restored:
                    msg += "Config settings restored\n"
                messagebox.showinfo("Restore Complete", msg)
            else:
                messagebox.showinfo("Restore Complete", 
                    "No new data was added.\nAll items in the backup already exist in the database.")
            
            return True
            
        except Exception as e:
            # Restore original DB_TYPE on error
            try:
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                pass
            
            messagebox.showerror("Restore Error", f"Failed to restore:\n{e}")
            return False
    
    def _restore_related_tables(self, backup_data, database):
        """Restore related tables like selected_terrains, a_selected_purposes, etc.
        
        Handles both old backup files (which used wrong key names like
        'session_terrains') and new ones (which use correct names like
        'selected_terrains').
        """
        from sqlalchemy import text
        
        # Map: (JSON key names to try) â†’ actual DB table name
        # First key is the correct name (new backups), second is old wrong name.
        table_mappings = [
            (["selected_terrains", "session_terrains"], "selected_terrains"),
            (["a_selected_purposes", "session_purposes"], "a_selected_purposes"),
            (["subject_responses"], "subject_responses"),
            (["t_selected_terrains", "t_session_terrains"], "t_selected_terrains"),
            (["t_selected_purposes", "t_session_purposes"], "t_selected_purposes"),
            (["t_distractions", "t_session_distractions"], "t_distractions"),
        ]
        
        for json_keys, db_table in table_mappings:
            # Find data under any of the possible key names
            rows = None
            for key in json_keys:
                if key in backup_data:
                    rows = backup_data[key]
                    break
            
            if not rows:
                continue
            
            for row in rows:
                try:
                    with database.get_connection() as conn:
                        columns = [k for k in row.keys() if k != 'id']
                        placeholders = [f":{k}" for k in columns]
                        sql = f"INSERT OR IGNORE INTO {db_table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                        params = {k: row.get(k) for k in columns}
                        conn.execute(text(sql), params)
                        conn.commit()
                except:
                    pass
    
    def _restore_sessions_from_backup_folder(self, json_folder, db_type):
        """
        Restore sessions from JSON backup files in a specific folder.
        
        Args:
            json_folder: Path to folder containing session JSON files
            db_type: Database type to restore to
            
        Returns:
            int: Number of sessions restored
        """
        import database
        
        json_files = list(json_folder.glob("*session_*.json"))
        if not json_files:
            return 0
        
        restored_count = 0
        
        old_db_type = None
        try:
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            from database import engine
            engine.dispose()
            from importlib import reload
            reload(database)
            
            for json_file in sorted(json_files):
                try:
                    with open(json_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Check if session already exists
                    session_num = session_data.get('session_number')
                    date_str = session_data.get('date')
                    dog_name = session_data.get('dog_name')
                    
                    # Handle image_files - convert list to JSON string if needed
                    image_files = session_data.get('image_files', session_data.get('map_files', []))
                    if isinstance(image_files, list):
                        image_files_json = json.dumps(image_files)
                    else:
                        image_files_json = image_files or ''
                    
                    with database.get_connection() as conn:
                        # Check for existing session
                        result = conn.execute(
                            text("SELECT id FROM training_sessions WHERE session_number = :num AND date = :date AND dog_name = :dog"),
                            {"num": session_num, "date": date_str, "dog": dog_name}
                        )
                        if result.fetchone():
                            continue  # Skip existing session
                        
                        # Insert session - column names must match schema.py
                        conn.execute(
                            text("""
                                INSERT INTO training_sessions (
                                    session_number, date, dog_name, location, handler,
                                    weather, temperature, wind_direction, wind_speed,
                                    session_purpose, field_support, search_area_size,
                                    num_subjects, handler_knowledge, search_type,
                                    drive_level, subjects_found, comments, image_files,
                                    user_name
                                ) VALUES (
                                    :session_number, :date, :dog_name, :location, :handler,
                                    :weather, :temperature, :wind_direction, :wind_speed,
                                    :session_purpose, :field_support, :search_area_size,
                                    :num_subjects, :handler_knowledge, :search_type,
                                    :drive_level, :subjects_found, :comments, :image_files,
                                    :user_name
                                )
                            """),
                            {
                                "session_number": session_num,
                                "date": date_str,
                                "dog_name": dog_name,
                                "location": session_data.get('location', ''),
                                "handler": session_data.get('handler_name', session_data.get('handler', '')),
                                "weather": session_data.get('weather', ''),
                                "temperature": session_data.get('temperature', ''),
                                "wind_direction": session_data.get('wind_direction', ''),
                                "wind_speed": session_data.get('wind_speed', ''),
                                "session_purpose": session_data.get('session_purpose', ''),
                                "field_support": session_data.get('field_support', ''),
                                "search_area_size": session_data.get('search_area_size', ''),
                                "num_subjects": session_data.get('num_subjects', ''),
                                "handler_knowledge": session_data.get('handler_knowledge', ''),
                                "search_type": session_data.get('search_type', ''),
                                "drive_level": session_data.get('drive_level', ''),
                                "subjects_found": session_data.get('subjects_found', ''),
                                "comments": session_data.get('notes', session_data.get('comments', '')),
                                "image_files": image_files_json,
                                "user_name": session_data.get('user_name', get_username())
                            }
                        )
                        conn.commit()
                        
                        # Get inserted session ID
                        result = conn.execute(text("SELECT last_insert_rowid()"))
                        session_id = result.fetchone()[0]
                        
                        # Restore terrain types for this session
                        terrains = session_data.get('selected_terrains', session_data.get('terrain_types', session_data.get('terrains', [])))
                        for terrain in terrains:
                            try:
                                conn.execute(
                                    text("INSERT INTO selected_terrains (session_id, terrain_name, user_name) VALUES (:sid, :name, :user)"),
                                    {"sid": session_id, "name": terrain, "user": get_username()}
                                )
                            except:
                                pass
                        
                        # Restore subject responses
                        responses = session_data.get('subject_responses', [])
                        for resp in responses:
                            try:
                                conn.execute(
                                    text("""INSERT INTO subject_responses 
                                           (session_id, subject_number, tfr, refind, user_name)
                                           VALUES (:sid, :num, :tfr, :refind, :user)"""),
                                    {"sid": session_id, "num": resp.get('subject_number', 1),
                                     "tfr": resp.get('tfr', ''), 
                                     "refind": resp.get('refind', ''),
                                     "user": get_username()}
                                )
                            except:
                                pass
                        
                        conn.commit()
                        restored_count += 1
                        
                except Exception as e:
                    # print(f"Failed to restore session from {json_file}: {e}")
                    pass
            
            # Restore original DB_TYPE
            if old_db_type:
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
                
        except Exception as e:
            # print(f"Error during session restore: {e}")
            if old_db_type:
                try:
                    import config
                    config.DB_TYPE = old_db_type
                    database.engine.dispose()
                    from importlib import reload
                    reload(database)
                except:
                    pass
        
        return restored_count
    
    def restore_from_json_backups(self, db_type):
        """Restore database from JSON backup files in the PRIMARY storage folder"""
        from ui_utils import get_primary_json_folder
        
        # Get primary JSON folder (from sv.db_path/JSON)
        backup_path = get_primary_json_folder()
        if not backup_path:
            # Fall back to checking sv.backup_folder for backward compatibility
            backup_folder = sv.backup_folder.get().strip()
            if backup_folder:
                # Check if it's the old-style direct JSON folder or new-style with subfolder
                test_path = Path(backup_folder)
                if (test_path / "JSON").exists():
                    backup_path = test_path / "JSON"
                elif test_path.exists():
                    backup_path = test_path
            
        if not backup_path or not backup_path.exists():
            # No backup folder available, skip silently
            return False
        
        # Find all session JSON files (both old and new format)
        # Old format: session_<number>_<date>.json
        # New format: <dogname>_session_<number>_<date>.json
        json_files = list(backup_path.glob("*session_*.json"))
        if not json_files:
            # No backup files found, skip silently (this is normal for new installations)
            return False
        
        # Ask user to confirm restore
        result = messagebox.askyesno(
            "Restore from Backups",
            f"Found {len(json_files)} session backup files.\n\n"
            f"Do you want to restore these sessions to the new database?",
            icon='question'
        )
        
        if not result:
            return False
        
        # Restore sessions
        # Show working dialog for networked databases
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.ui.root, "Restoring", 
                                         f"Restoring {len(json_files)} sessions to {db_type} database...")
            self.ui.root.update()
        else:
            working_dialog = None
        
        try:
            import config
            old_db_type = config.DB_TYPE
            config.DB_TYPE = db_type
            
            from database import engine
            engine.dispose()
            from importlib import reload
            import database
            reload(database)
            
            restored_count = 0
            failed_count = 0
            dog_names = set()  # Collect unique dog names
            location_names = set()  # Collect unique location names
            
            for json_file in sorted(json_files):
                try:
                    with open(json_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Collect dog name for later insertion
                    dog_name = session_data.get('dog_name')
                    if dog_name:
                        dog_names.add(dog_name)
                    
                    # Collect location name for later insertion
                    location = session_data.get('location')
                    if location:
                        location_names.add(location)
                    
                    # Insert into database
                    with database.get_connection() as conn:
                        # Convert image_files list to JSON string if present
                        image_files = session_data.get('image_files', [])
                        image_files_json = json.dumps(image_files) if isinstance(image_files, list) else (image_files or "")
                        
                        conn.execute(
                            text("""
                                INSERT INTO training_sessions 
                                (date, session_number, handler, session_purpose, field_support, dog_name, location,
                                 search_area_size, num_subjects, handler_knowledge, weather, temperature, 
                                 wind_direction, wind_speed, search_type, drive_level, subjects_found, comments, image_files, user_name)
                                VALUES (:date, :session_number, :handler, :session_purpose, :field_support, :dog_name, :location,
                                        :search_area_size, :num_subjects, :handler_knowledge, :weather, :temperature, 
                                        :wind_direction, :wind_speed, :search_type, :drive_level, :subjects_found, :comments, :image_files, :user_name)
                            """),
                            {
                                "date": session_data.get('date'),
                                "session_number": session_data.get('session_number'),
                                "handler": session_data.get('handler'),
                                "session_purpose": session_data.get('session_purpose'),
                                "field_support": session_data.get('field_support'),
                                "dog_name": session_data.get('dog_name'),
                                "location": session_data.get('location'),
                                "search_area_size": session_data.get('search_area_size'),
                                "num_subjects": session_data.get('num_subjects'),
                                "handler_knowledge": session_data.get('handler_knowledge'),
                                "weather": session_data.get('weather'),
                                "temperature": session_data.get('temperature'),
                                "wind_direction": session_data.get('wind_direction'),
                                "wind_speed": session_data.get('wind_speed'),
                                "search_type": session_data.get('search_type'),
                                "drive_level": session_data.get('drive_level'),
                                "subjects_found": session_data.get('subjects_found'),
                                "comments": session_data.get('comments', ''),
                                "image_files": image_files_json,
                                "user_name": session_data.get('user_name', get_username())
                            }
                        )
                        conn.commit()
                        
                        # Get the session_id we just inserted (for terrains and subject responses)
                        result = conn.execute(
                            text("SELECT id FROM training_sessions WHERE session_number = :session_number AND dog_name = :dog_name"),
                            {"session_number": session_data.get('session_number'), "dog_name": session_data.get('dog_name')}
                        )
                        session_row = result.fetchone()
                        
                        if session_row:
                            session_id = session_row[0]
                            
                            # Insert selected terrains if present in JSON
                            selected_terrains = session_data.get('selected_terrains', [])
                            for terrain_name in selected_terrains:
                                conn.execute(
                                    text("""
                                        INSERT INTO selected_terrains (session_id, terrain_name, user_name)
                                        VALUES (:session_id, :terrain_name, :user_name)
                                    """),
                                    {
                                        "session_id": session_id,
                                        "terrain_name": terrain_name,
                                        "user_name": session_data.get('user_name', get_username())
                                    }
                                )
                            
                            # Insert subject responses if present in JSON
                            subject_responses = session_data.get('subject_responses', [])
                            for response in subject_responses:
                                if isinstance(response, dict):
                                    conn.execute(
                                        text("""
                                            INSERT INTO subject_responses (session_id, subject_number, tfr, refind, user_name)
                                            VALUES (:session_id, :subject_number, :tfr, :refind, :user_name)
                                        """),
                                        {
                                            "session_id": session_id,
                                            "subject_number": response.get('subject_number'),
                                            "tfr": response.get('tfr'),
                                            "refind": response.get('refind'),
                                            "user_name": session_data.get('user_name', get_username())
                                        }
                                    )
                            
                            conn.commit()
                    
                    restored_count += 1
                    
                except Exception as e:
                    # print(f"Failed to restore {json_file.name}: {e}")
                    failed_count += 1
            
            # Now insert all unique dog names into dogs table
            dogs_added = 0
            for dog_name in sorted(dog_names):
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO dogs (name, user_name) VALUES (:name, :user_name)"),
                            {"name": dog_name, "user_name": get_username()}
                        )
                        conn.commit()
                    dogs_added += 1
                except Exception as e:
                    # Dog might already exist (UNIQUE constraint), that's OK
                    if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                        pass  # Duplicate is OK, continue with next dog
                    else:
                        pass  # Other errors are logged but don't stop the process
            
            # Now insert all unique location names into training_locations table
            locations_added = 0
            for location in sorted(location_names):
                try:
                    with database.get_connection() as conn:
                        conn.execute(
                            text("INSERT INTO training_locations (name, user_name) VALUES (:name, :user_name)"),
                            {"name": location, "user_name": get_username()}
                        )
                        conn.commit()
                    locations_added += 1
                except Exception as e:
                    # Location might already exist (UNIQUE constraint), that's OK
                    if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                        pass  # Duplicate is OK, continue with next location
                    else:
                        pass  # Other errors are logged but don't stop the process
            
            # Restore original DB_TYPE
            config.DB_TYPE = old_db_type
            database.engine.dispose()
            reload(database)
            
            # Refresh dog list in UI
            self.ui.load_dogs_from_database()
            if hasattr(self.ui, 'a_dog_combo'):
                self.ui.refresh_dog_list()
            
            # Refresh location list in UI
            self.ui.load_locations_from_database()
            if hasattr(self.ui, 'a_location_combo'):
                self.ui.refresh_location_list()
            
            # Also try to restore from config backup if it exists
            settings_restored = False
            terrain_added = 0
            distraction_added = 0
            
            # Try new config file first, then old settings file
            settings_path = backup_path / ".training_log_config.json"
            if not settings_path.exists():
                settings_path = backup_path / "airscenting_settings.json"
            
            if settings_path.exists():
                try:
                    with open(settings_path, 'r') as f:
                        settings = json.load(f)
                    
                    # Insert terrain types
                    terrain_types = settings.get("terrain_types", [])
                    for terrain in terrain_types:
                        try:
                            with database.get_connection() as conn:
                                conn.execute(
                                    text("INSERT INTO terrain_types (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": terrain, "user_name": get_username()}
                                )
                                conn.commit()
                            terrain_added += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e) and "duplicate key" not in str(e):
                                # print(f"Failed to add terrain type '{terrain}': {e}")
                                pass
                    
                    # Insert distraction types
                    distraction_types = settings.get("distraction_types", [])
                    for distraction in distraction_types:
                        try:
                            with database.get_connection() as conn:
                                conn.execute(
                                    text("INSERT INTO distraction_types (name, user_name) VALUES (:name, :user_name)"),
                                    {"name": distraction, "user_name": get_username()}
                                )
                                conn.commit()
                            distraction_added += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e) and "duplicate key" not in str(e):
                                # print(f"Failed to add distraction type '{distraction}': {e}")
                                pass
                    
                    # Refresh UI
                    self.ui.load_terrain_from_database()
                    self.ui.load_distraction_from_database()
                    # Also refresh Entry tab terrain combobox
                    if hasattr(self.ui, 'a_terrain_combo'):
                        self.ui.refresh_terrain_list()
                    
                    settings_restored = True
                    
                except Exception as e:
                    # print(f"Could not restore settings backup: {e}")
                    pass
            
            # Show results
            if restored_count > 0:
                msg = f"Successfully restored {restored_count} session(s)"
                if dogs_added > 0:
                    msg += f"\nAdded {dogs_added} dog(s) to database"
                if locations_added > 0:
                    msg += f"\nAdded {locations_added} location(s) to database"
                if settings_restored:
                    if terrain_added > 0:
                        msg += f"\nAdded {terrain_added} terrain type(s) from settings"
                    if distraction_added > 0:
                        msg += f"\nAdded {distraction_added} distraction type(s) from settings"
                if failed_count > 0:
                    msg += f"\n{failed_count} session(s) failed to restore"
                messagebox.showinfo("Restore Complete", msg)
                return True
            else:
                messagebox.showerror("Restore Failed", "No sessions were restored")
                return False
            
        except Exception as e:
            # Restore original DB_TYPE on error
            try:
                import config
                import database
                from importlib import reload
                config.DB_TYPE = old_db_type
                database.engine.dispose()
                reload(database)
            except:
                pass
            
            messagebox.showerror("Restore Error", f"Failed to restore sessions:\n{e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
    
    def offer_load_default_types(self, db_type):
        """Offer to load default terrain and distraction types into new database"""
        result = messagebox.askyesno(
            "Load Default Types?",
            "Would you like to load the default terrain and distraction types?\n\n"
            "Terrain types (17):\n"
            "Urban, Rural, Forest, Scrub, Desert, Sandy, Rocky, City park, Meadow, etc.\n\n"
            "Distraction types (7):\n"
            "Critter, Horse, Loud noise, Motorcycle, Hikers, Cow, Vehicle"
        )
        
        if not result:
            return
        
        # Use DatabaseManager to properly load defaults with sort_order
        db_mgr = get_db_manager(db_type)
        
        # Show working dialog for networked databases
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.ui.root, "Loading Defaults", 
                                         f"Loading default types to {db_type} database...")
            self.ui.root.update()
        else:
            working_dialog = None
        
        try:
            terrain_success, terrain_msg = db_mgr.restore_default_terrain_types()
            distraction_success, distraction_msg = db_mgr.restore_default_distraction_types()
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)
        
        # Refresh UI - both Setup tab AND Entry tab
        self.ui.load_terrain_from_database()  # Setup tab treeview
        self.ui.load_distraction_from_database()  # Setup tab treeview
        
        # CRITICAL: Also refresh Entry tab comboboxes!
        if hasattr(self.ui, 'a_terrain_combo'):
            self.ui.refresh_terrain_list()  # Entry tab terrain combobox
        
        # Show summary
        if terrain_success and distraction_success:
            sv.show_status_message(f"{terrain_msg}; {distraction_msg}", "info")
            # Auto-backup settings after loading defaults
            self.save_settings_backup()
        else:
            errors = []
            if not terrain_success:
                errors.append(f"Terrain: {terrain_msg}")
            if not distraction_success:
                errors.append(f"Distraction: {distraction_msg}")
            messagebox.showerror("Error", "\n".join(errors))
    
    def ensure_db_ready(self):
        """Ensure database connection is ready (password set for networked DBs)"""
        db_type = sv.db_type.get()
        if db_type in ["postgres", "supabase", "mysql"]:
            # Check if password field exists yet (it's created in setup_setup_tab)
            if not hasattr(self.ui, 'db_password_var'):
                return  # Too early in initialization
            
            password = sv.db_password.get().strip()
            
            # If password not loaded yet, try loading from encrypted storage
            if not password and hasattr(self.ui, 'config'):
                from password_manager import get_decrypted_password, check_crypto_available
                if check_crypto_available():
                    saved_password = get_decrypted_password(self.ui.config, db_type)
                    if saved_password:
                        sv.db_password.set(saved_password)
                        password = saved_password
            
            # Set password in database config
            if password:
                self.ui.set_db_password()
        
        # Run database migrations to add any new columns
        # This is safe to run multiple times - migrations check if columns exist first
        try:
            from schema import migrate_add_a_percent_searched_column
            migrate_add_a_percent_searched_column()
        except Exception as e:
            # Silently continue - migrations might fail if DB not initialized yet
            pass
