"""
SPDX-License-Identifier: GPL-3.0-or-later

Copyright (C) 2026 Al Gelders

This file is part of the SAR Dog Training Logger

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
Session Lock Manager

Manages a lock file in the secondary backup folder to prevent two users
from running the application simultaneously against the same shared backup.
The lock file is a JSON file containing the machine name, user name, and
the time of the last update.

On startup:
    - If no lock exists, create one and proceed.
    - If a lock exists from the same machine/user, overwrite and proceed.
    - If a lock exists from a different machine/user, prompt the user to
      either exit immediately or take over the lock.

While running:
    - User activity (keystrokes and mouse clicks) is tracked.
    - Every 5 minutes of activity, the lock file timestamp is refreshed.
    - After 10 minutes of inactivity, a popup asks whether to continue.
    - If the user responds "No" or does not respond within another
      10 minutes, the application exits without saving unsaved UI data.

On exit:
    - The lock file is deleted (after the normal exit backup has been written).
"""

import json
import socket
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime, timedelta
from getpass import getuser


# =========================================================================
# CONSTANTS
# =========================================================================

LOCK_FILENAME = "session_lock.json"

# How often (seconds) the periodic check timer fires
_CHECK_INTERVAL_SEC = 60

# Refresh the lock file if it has not been updated in this many minutes
_LOCK_REFRESH_MINUTES = 5

# Show the inactivity prompt after this many minutes with no input
_INACTIVE_PROMPT_MINUTES = 10

# Auto-exit if the inactivity prompt is not answered within this many minutes
_INACTIVE_TIMEOUT_MINUTES = 10


# =========================================================================
# IDENTITY HELPERS
# =========================================================================

def _get_machine_name():
    """Return the hostname of the current machine."""
    try:
        return socket.gethostname()
    except Exception:
        return "unknown-machine"


def _get_user_name():
    """Return the OS login name of the current user."""
    try:
        return getuser()
    except Exception:
        return "unknown-user"


def _format_elapsed(dt):
    """Return a human-readable string for time elapsed since *dt*."""
    delta = datetime.now() - dt
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return "less than a minute ago"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    remaining_min = minutes % 60
    if hours < 24:
        if remaining_min:
            return f"{hours} hour{'s' if hours != 1 else ''} and {remaining_min} minute{'s' if remaining_min != 1 else ''} ago"
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


# =========================================================================
# LOCK MANAGER CLASS
# =========================================================================

class LockManager:
    """
    Manages a session lock file in the secondary backup folder.

    Usage
    -----
    1. Create an instance, passing the tkinter root and the secondary
       backup folder path.
    2. Call ``check_startup_lock()``; if it returns False the caller
       should immediately exit.
    3. Call ``start()`` once the UI is ready to begin activity tracking
       and periodic lock updates.
    4. Call ``release()`` during normal shutdown (after backups) to
       delete the lock file and cancel timers.
    """

    def __init__(self, root, secondary_folder):
        """
        Parameters
        ----------
        root : tk.Tk
            The main application window (needed for ``after`` timers and
            event bindings).
        secondary_folder : str or Path
            Path to the secondary backup folder.  The lock file is written
            directly inside this folder (not in its JSON subfolder).
        """
        self.root = root
        self.secondary_folder = Path(secondary_folder) if secondary_folder else None
        self.machine = _get_machine_name()
        self.user = _get_user_name()

        # Timestamps for activity and lock refresh tracking
        self._last_activity_time = datetime.now()
        self._last_lock_write_time = None

        # Timer IDs (so they can be cancelled)
        self._periodic_timer_id = None
        self._dialog_timeout_id = None

        # Guard against re-entrant inactivity prompts
        self._inactive_dialog_open = False

        # Callback set by the main app – called for forced exits
        self.force_exit_callback = None

    # -----------------------------------------------------------------
    # Lock file path
    # -----------------------------------------------------------------

    def _lock_path(self):
        """Return the full Path to the lock file, or None."""
        if self.secondary_folder and self.secondary_folder.exists():
            return self.secondary_folder / LOCK_FILENAME
        return None

    # -----------------------------------------------------------------
    # Low-level lock I/O
    # -----------------------------------------------------------------

    def _read_lock(self):
        """Read and return the lock file contents as a dict, or None."""
        path = self._lock_path()
        if path and path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _write_lock(self):
        """Write (or overwrite) the lock file with current identity and time."""
        path = self._lock_path()
        if not path:
            return
        try:
            data = {
                "machine": self.machine,
                "user": self.user,
                "last_update": datetime.now().isoformat()
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._last_lock_write_time = datetime.now()
        except Exception:
            pass  # Non-fatal; we'll try again at the next refresh

    def _delete_lock(self):
        """Delete the lock file if it exists."""
        path = self._lock_path()
        if path and path.exists():
            try:
                path.unlink()
            except Exception:
                pass

    def _is_own_lock(self, lock_data):
        """Return True if *lock_data* was written by this machine/user."""
        if not lock_data:
            return False
        return (lock_data.get("machine") == self.machine
                and lock_data.get("user") == self.user)

    # -----------------------------------------------------------------
    # Startup check
    # -----------------------------------------------------------------

    def check_startup_lock(self):
        """
        Inspect the lock file at startup.

        Returns
        -------
        bool
            True  – the application may proceed (lock acquired).
            False – the user chose to exit; the caller should quit
                    immediately without writing any backup files.
        """
        if not self._lock_path():
            return True  # No secondary folder configured – nothing to lock

        lock_data = self._read_lock()

        if lock_data is None or self._is_own_lock(lock_data):
            # No lock, or our own stale lock – (re)acquire
            self._write_lock()
            return True

        # Lock belongs to someone else
        other_user = lock_data.get("user", "unknown")
        other_machine = lock_data.get("machine", "unknown")
        last_update_str = lock_data.get("last_update", "")
        try:
            last_update_dt = datetime.fromisoformat(last_update_str)
            elapsed_text = _format_elapsed(last_update_dt)
        except Exception:
            elapsed_text = "unknown time ago"

        msg = (
            f"Another user appears to be running this application.\n\n"
            f"  User:     {other_user}\n"
            f"  Machine:  {other_machine}\n"
            f"  Last active:  {elapsed_text}\n\n"
            f"If that session is no longer active you may take over.\n"
            f"Otherwise, please exit to avoid data conflicts.\n\n"
            f"Take over the lock and continue?"
        )

        answer = messagebox.askyesno("Session Lock Detected", msg, icon="warning")
        if answer:
            # User wants to take over
            self._delete_lock()
            self._write_lock()
            return True
        else:
            # User chose to exit immediately
            return False

    # -----------------------------------------------------------------
    # Activity tracking
    # -----------------------------------------------------------------

    def _on_user_activity(self, _event=None):
        """Called on every keypress or mouse click in the application."""
        self._last_activity_time = datetime.now()

    def _minutes_since_last_activity(self):
        delta = datetime.now() - self._last_activity_time
        return delta.total_seconds() / 60.0

    # -----------------------------------------------------------------
    # Periodic check
    # -----------------------------------------------------------------

    def _periodic_check(self):
        """Called every _CHECK_INTERVAL_SEC seconds while the app is running."""
        try:
            minutes_idle = self._minutes_since_last_activity()

            if minutes_idle < _INACTIVE_PROMPT_MINUTES:
                # User is active – refresh the lock file if it is stale
                if self._last_lock_write_time is None:
                    self._write_lock()
                else:
                    minutes_since_write = (
                        (datetime.now() - self._last_lock_write_time).total_seconds() / 60.0
                    )
                    if minutes_since_write >= _LOCK_REFRESH_MINUTES:
                        self._write_lock()
            else:
                # User appears inactive
                if not self._inactive_dialog_open:
                    self._show_inactive_prompt()
        except Exception:
            pass  # Keep the timer alive regardless of errors

        # Schedule next check
        self._periodic_timer_id = self.root.after(
            _CHECK_INTERVAL_SEC * 1000, self._periodic_check
        )

    # -----------------------------------------------------------------
    # Inactivity prompt
    # -----------------------------------------------------------------

    def _show_inactive_prompt(self):
        """Show a popup asking the inactive user whether to continue."""
        self._inactive_dialog_open = True

        dialog = tk.Toplevel(self.root)
        dialog.title("Inactivity Warning")
        dialog.geometry("400x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent X close
        dialog.attributes('-topmost', True)

        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 90
        dialog.geometry(f"+{x}+{y}")

        minutes_idle = int(self._minutes_since_last_activity())
        tk.Label(
            dialog,
            text=(f"You have been inactive for {minutes_idle} minutes.\n\n"
                  f"If you do not respond within {_INACTIVE_TIMEOUT_MINUTES} minutes\n"
                  f"the application will exit automatically."),
            justify="center",
            padx=20,
            pady=15,
            wraplength=360
        ).pack()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)

        def on_continue():
            _cancel_timeout()
            self._last_activity_time = datetime.now()
            self._write_lock()
            self._inactive_dialog_open = False
            dialog.destroy()

        def on_exit():
            _cancel_timeout()
            self._inactive_dialog_open = False
            dialog.destroy()
            self._force_exit()

        def _on_timeout():
            self._inactive_dialog_open = False
            dialog.destroy()
            self._force_exit()

        def _cancel_timeout():
            if self._dialog_timeout_id is not None:
                try:
                    self.root.after_cancel(self._dialog_timeout_id)
                except Exception:
                    pass
                self._dialog_timeout_id = None

        tk.Button(btn_frame, text="Continue Working", command=on_continue,
                  width=18, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Exit Now", command=on_exit,
                  width=12).pack(side=tk.LEFT, padx=10)

        # Auto-exit timer
        self._dialog_timeout_id = self.root.after(
            _INACTIVE_TIMEOUT_MINUTES * 60 * 1000, _on_timeout
        )

    # -----------------------------------------------------------------
    # Force exit (inactivity timeout or user chose "Exit Now")
    # -----------------------------------------------------------------

    def _force_exit(self):
        """Exit the application immediately.

        Writes the full backup and deletes the lock, but does NOT prompt
        about unsaved UI form data.
        """
        # Perform exit backup first (callback does _perform_exit_backup)
        if self.force_exit_callback:
            try:
                self.force_exit_callback()
            except Exception:
                pass

        # Delete lock file after backup is written
        try:
            self._delete_lock()
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Public API: start / release
    # -----------------------------------------------------------------

    def start(self):
        """Begin activity tracking and periodic lock refresh.

        Call this after the UI is fully constructed.
        """
        if not self._lock_path():
            return  # No secondary folder – nothing to do

        # Bind activity events on the root window
        self.root.bind_all("<Any-KeyPress>", self._on_user_activity, add="+")
        self.root.bind_all("<Any-ButtonPress>", self._on_user_activity, add="+")

        # Write the initial lock (or refresh it)
        self._write_lock()

        # Start the periodic timer
        self._periodic_timer_id = self.root.after(
            _CHECK_INTERVAL_SEC * 1000, self._periodic_check
        )

    def release(self):
        """Delete the lock file and cancel all timers.

        Call this during normal shutdown, after backups have been written.
        """
        # Cancel timers
        if self._periodic_timer_id is not None:
            try:
                self.root.after_cancel(self._periodic_timer_id)
            except Exception:
                pass
            self._periodic_timer_id = None

        if self._dialog_timeout_id is not None:
            try:
                self.root.after_cancel(self._dialog_timeout_id)
            except Exception:
                pass
            self._dialog_timeout_id = None

        self._delete_lock()
