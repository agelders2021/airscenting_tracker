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
Stringvars Module - Central Storage for All Tkinter StringVars
Provides global sv variable for easy access throughout application

Usage:
    from sv import sv
    
    # Access anywhere:
    sv.date.set("2025-01-15")
    date = sv.date.get()
    
    # Clear form:
    sv.clear_session_fields()
    
    # Export all:
    data = sv.to_dict()
"""

import tkinter as tk
from datetime import datetime


class Stringvars:
    """Central storage for all Tkinter StringVars in the application"""
    
    def __init__(self, master=None):
        """
        Initialize all StringVars organized by category
        
        Args:
            master: The Tkinter root window (optional, uses default if None)
        """
        
        # ===== SESSION INFORMATION =====
        self.date = tk.StringVar(master=master, value=datetime.now().strftime("%Y-%m-%d"))
        self.session_number = tk.StringVar(master=master, value="1")
        self.handler = tk.StringVar(master=master)
        self.dog = tk.StringVar(master=master)
        
        # ===== SESSION DETAILS =====
        self.session_purpose = tk.StringVar(master=master)  # Legacy single-value field (kept for compatibility)
        self.a_purpose = tk.StringVar(master=master)  # Current dropdown selection for purpose accumulator
        self.field_support = tk.StringVar(master=master)
        
        # ===== SESSION PURPOSES (List of selected purposes for accumulator) =====
        self.a_purpose_list = []  # Accumulated session purposes for airscenting
        
        # ===== SEARCH PARAMETERS =====
        self.location = tk.StringVar(master=master)
        self.search_area_size = tk.StringVar(master=master)
        self.num_subjects = tk.StringVar(master=master)
        self.handler_knowledge = tk.StringVar(master=master)
        
        # ===== WEATHER CONDITIONS =====
        self.weather = tk.StringVar(master=master)
        self.temperature = tk.StringVar(master=master)
        self.wind_direction = tk.StringVar(master=master)
        self.wind_speed = tk.StringVar(master=master)
        
        # ===== SEARCH DETAILS =====
        self.search_type = tk.StringVar(master=master)
        self.terrain = tk.StringVar(master=master)  # Current terrain dropdown selection
        self.accumulated_terrain = tk.StringVar(master=master)  # Display of accumulated terrains
        
        # ===== SEARCH RESULTS =====
        self.drive_level = tk.StringVar(master=master)
        self.subjects_found = tk.StringVar(master=master)
        self.a_percent_searched = tk.StringVar(master=master)
        self.start_time = tk.StringVar(master=master)
        self.finish_time = tk.StringVar(master=master)
        
        # ===== TERRAIN (List of selected terrains) =====
        # Note: This is a list, not StringVar, to hold multiple selections
        self.terrain_list = []  
        
        # ===== TERRAIN TYPES AND DISTRACTION TYPES (Master lists from database) =====
        # These are the ordered lists used to populate combo boxes across all tabs
        self.terrain_types_list = []
        self.distraction_types_list = []
        
        # ===== SUBJECT RESPONSES (List of dicts) =====
        # Note: This holds structured data for subject responses
        self.subject_responses = []
        
        # ===== TRAILING SESSION INFORMATION =====
        self.t_date = tk.StringVar(master=master, value=datetime.now().strftime("%Y-%m-%d"))
        self.t_session = tk.StringVar(master=master, value="1")
        self.t_handler = tk.StringVar(master=master)
        self.t_dog = tk.StringVar(master=master)
        self.t_field_support = tk.StringVar(master=master)
        self.t_purpose = tk.StringVar(master=master)  # Current dropdown selection
        self.t_status = tk.StringVar(master=master, value="Ready")
        self.t_session_status_filter = tk.StringVar(master=master, value="active")  # Filter for session status
        
        # ===== TRAILING TRAIL DETAILS =====
        self.t_location = tk.StringVar(master=master)
        self.t_terrain = tk.StringVar(master=master)  # Current dropdown selection
        self.t_start_time = tk.StringVar(master=master)
        self.t_finish_time = tk.StringVar(master=master)
        self.t_trail_age = tk.StringVar(master=master)
        self.t_trail_length = tk.StringVar(master=master)
        self.t_difficulty = tk.StringVar(master=master)
        self.t_trail_layer = tk.StringVar(master=master)
        #self.t_cross_track_layer = tk.StringVar(master=master, value="None") ahg
        self.t_cross_track_layer = tk.StringVar(master=master)
        self.t_cross_track_age = tk.StringVar(master=master)
        
        # ===== TRAILING WEATHER WHEN LAYING =====
        self.t_weather_laying = tk.StringVar(master=master)
        self.t_temp_laying = tk.StringVar(master=master)
        self.t_wind_laying = tk.StringVar(master=master)
        self.t_wind_direction_laying = tk.StringVar(master=master)
        self.t_humidity_laying = tk.StringVar(master=master)
        
        # ===== TRAILING WEATHER WHEN RUNNING =====
        self.t_weather_running = tk.StringVar(master=master)
        self.t_temp_running = tk.StringVar(master=master)
        self.t_wind_running = tk.StringVar(master=master)
        self.t_wind_direction_running = tk.StringVar(master=master)
        self.t_humidity_running = tk.StringVar(master=master)
        
        # ===== TRAILING DOG BEHAVIOR =====
        self.t_start_behavior = tk.StringVar(master=master)
        self.t_consistency = tk.StringVar(master=master)
        self.t_head_pos = tk.StringVar(master=master)  # Hidden but kept for compatibility
        self.t_pace = tk.StringVar(master=master)
        self.t_indication = tk.StringVar(master=master)
        self.t_time = tk.StringVar(master=master)  # Time to complete
        self.t_success = tk.StringVar(master=master)  # Hidden but kept for compatibility
        
        # ===== TRAILING DISTRACTIONS =====
        self.t_distractions = tk.StringVar(master=master)  # Current dropdown selection
        self.t_distraction_response = tk.StringVar(master=master)
        self.t_accumulated_distractions = tk.StringVar(master=master)  # Display string
        
        # ===== TRAILING IMPRESSION =====
        self.t_impression = tk.StringVar(master=master)
        
        # ===== TRAILING LISTS (non-StringVar data) =====
        self.t_purpose_list = []  # Accumulated session purposes
        self.t_terrain_list = []  # Accumulated terrain types
        self.t_distractions_list = []  # List of {type, response} dicts
        self.t_map_files_list = []  # List of trail map file paths
        
        # ===== SETUP TAB - USER =====
        self.current_user = tk.StringVar(master=master)
        
        # ===== SETUP TAB - PATHS =====
        self.db_path = tk.StringVar(master=master)
        self.trail_maps_folder = tk.StringVar(master=master)
        self.backup_folder = tk.StringVar(master=master)
        self.pdf_folder = tk.StringVar(master=master)
        self.excel_folder = tk.StringVar(master=master)
        self.config_path = tk.StringVar(master=master)
        
        # ===== SETUP TAB - DATABASE =====
        self.db_type = tk.StringVar(master=master, value="sqlite")
        self.db_password = tk.StringVar(master=master)
        self.remember_password = tk.BooleanVar(master=master, value=False)
        self.show_password = tk.BooleanVar(master=master, value=False)  # For password visibility toggle
        
        # ===== SETUP TAB - DEFAULTS =====
        self.default_handler = tk.StringVar(master=master)
        
        # ===== SETUP TAB - ENTRY FIELDS =====
        self.new_location = tk.StringVar(master=master)
        self.new_dog = tk.StringVar(master=master)
        self.new_terrain = tk.StringVar(master=master)
        self.new_distraction = tk.StringVar(master=master)
        
        # ===== VIEW FILTERS =====
        self.view_filter = tk.StringVar(master=master, value="undeleted")  # For soft delete feature
        self.session_status_filter = tk.StringVar(master=master, value="active")  # Filter for session status
        
        # ===== STATUS BAR =====
        self.status = tk.StringVar(master=master, value="Ready")
        
        # ===== BACKUP STATUS FLAGS =====
        # Track if user has been notified about secondary backup folder being unavailable
        # Resets on each application startup; only notify once per session
        self.secondary_unavailable_notified = False
        
        # Track if background sync is in progress (blocks Edit/Delete operations)
        self.sync_in_progress = False
        
        # Track if a database restore has occurred and restart is required
        # When True, user must restart the program before entering session tabs
        self.restart_required = False
    
    # ========================================
    # HELPER METHODS - SESSION OPERATIONS
    # ========================================
    
    def clear_session_fields(self, keep_handler=True, keep_dog=True):
        """
        Clear all session entry fields
        
        Args:
            keep_handler: If True, preserve handler name (default: True)
            keep_dog: If True, preserve dog selection (default: True)
        """
        self.date.set(datetime.now().strftime("%Y-%m-%d"))
        self.session_number.set("")
        
        if not keep_handler:
            self.handler.set("")
        
        if not keep_dog:
            self.dog.set("")
        
        # Session details
        self.session_purpose.set("")
        self.a_purpose.set("")
        self.a_purpose_list.clear()
        self.field_support.set("")
        
        # Search parameters
        self.location.set("")
        self.search_area_size.set("")
        self.num_subjects.set("")
        self.handler_knowledge.set("")
        
        # Weather
        self.weather.set("")
        self.temperature.set("")
        self.wind_direction.set("")
        self.wind_speed.set("")
        
        # Search details
        self.search_type.set("")
        
        # Results
        self.drive_level.set("")
        self.subjects_found.set("")
        self.a_percent_searched.set("")
        self.start_time.set("")
        self.finish_time.set("")
        
        # Terrain, purposes, and subject responses
        self.terrain_list.clear()
        self.a_purpose_list.clear()
        self.subject_responses.clear()
    
    def clear_setup_entry_fields(self):
        """Clear all entry fields on setup tab"""
        self.new_location.set("")
        self.new_dog.set("")
        self.new_terrain.set("")
        self.new_distraction.set("")
    
    def clear_trailing_session_fields(self, keep_handler=True, keep_dog=True):
        """
        Clear all trailing session entry fields
        
        Args:
            keep_handler: If True, preserve handler name (default: True)
            keep_dog: If True, preserve dog selection (default: True)
        """
        self.t_date.set(datetime.now().strftime("%Y-%m-%d"))
        self.t_session.set("")
        
        if not keep_handler:
            self.t_handler.set("")
        
        if not keep_dog:
            self.t_dog.set("")
        
        # Session details
        self.t_field_support.set("")
        self.t_purpose.set("")
        
        # Trail details
        self.t_location.set("")
        self.t_terrain.set("")
        self.t_start_time.set("")
        self.t_finish_time.set("")
        self.t_trail_age.set("")
        self.t_trail_length.set("")
        self.t_difficulty.set("")
        self.t_trail_layer.set("")
        self.t_cross_track_layer.set("None")
        self.t_cross_track_age.set("")
        
        # Weather laying
        self.t_weather_laying.set("")
        self.t_temp_laying.set("")
        self.t_wind_laying.set("")
        self.t_wind_direction_laying.set("")
        self.t_humidity_laying.set("")
        
        # Weather running
        self.t_weather_running.set("")
        self.t_temp_running.set("")
        self.t_wind_running.set("")
        self.t_wind_direction_running.set("")
        self.t_humidity_running.set("")
        
        # Behavior
        self.t_start_behavior.set("")
        self.t_consistency.set("")
        self.t_head_pos.set("")
        self.t_pace.set("")
        self.t_indication.set("")
        self.t_time.set("")
        self.t_success.set("")
        
        # Distractions
        self.t_distractions.set("")
        self.t_distraction_response.set("")
        self.t_accumulated_distractions.set("")
        
        # Impression
        self.t_impression.set("")
        
        # Lists
        self.t_purpose_list.clear()
        self.t_terrain_list.clear()
        self.t_distractions_list.clear()
        self.t_map_files_list.clear()
    
    # ========================================
    # EXPORT/IMPORT METHODS
    # ========================================
    
    def to_dict(self):
        """
        Export all session data as dictionary
        
        Returns:
            dict: All session field values
        """
        return {
            # Session info
            'date': self.date.get(),
            'session_number': self.session_number.get(),
            'handler': self.handler.get(),
            'dog_name': self.dog.get(),
            
            # Session details
            'session_purpose': self.session_purpose.get(),
            'field_support': self.field_support.get(),
            
            # Search parameters
            'location': self.location.get(),
            'search_area_size': self.search_area_size.get(),
            'num_subjects': self.num_subjects.get(),
            'handler_knowledge': self.handler_knowledge.get(),
            
            # Weather
            'weather': self.weather.get(),
            'temperature': self.temperature.get(),
            'wind_direction': self.wind_direction.get(),
            'wind_speed': self.wind_speed.get(),
            
            # Search details
            'search_type': self.search_type.get(),
            
            # Results
            'drive_level': self.drive_level.get(),
            'subjects_found': self.subjects_found.get(),
            'a_percent_searched': self.a_percent_searched.get(),
            'start_time': self.start_time.get(),
            'finish_time': self.finish_time.get(),
            
            # Terrain (list)
            'terrain_list': self.terrain_list.copy(),
            
            # Subject responses (list of dicts)
            'subject_responses': self.subject_responses.copy()
        }
    
    def from_dict(self, data):
        """
        Import session data from dictionary
        
        Args:
            data: Dictionary with session field values
        """
        # Session info
        self.date.set(data.get('date', ''))
        self.session_number.set(str(data.get('session_number', '')))
        self.handler.set(data.get('handler', ''))
        self.dog.set(data.get('dog_name', ''))
        
        # Session details
        self.session_purpose.set(data.get('session_purpose', ''))
        self.field_support.set(data.get('field_support', ''))
        
        # Search parameters
        self.location.set(data.get('location', ''))
        self.search_area_size.set(data.get('search_area_size', ''))
        self.num_subjects.set(data.get('num_subjects', ''))
        self.handler_knowledge.set(data.get('handler_knowledge', ''))
        
        # Weather
        self.weather.set(data.get('weather', ''))
        self.temperature.set(data.get('temperature', ''))
        self.wind_direction.set(data.get('wind_direction', ''))
        self.wind_speed.set(data.get('wind_speed', ''))
        
        # Search details
        self.search_type.set(data.get('search_type', ''))
        
        # Results
        self.drive_level.set(data.get('drive_level', ''))
        self.subjects_found.set(data.get('subjects_found', ''))
        self.a_percent_searched.set(data.get('a_percent_searched', ''))
        self.start_time.set(data.get('start_time', ''))
        self.finish_time.set(data.get('finish_time', ''))
        
        # Terrain (list)
        self.terrain_list = data.get('terrain_list', []).copy()
        
        # Subject responses (list of dicts)
        self.subject_responses = data.get('subject_responses', []).copy()
    
    # ========================================
    # TRAILING SESSION EXPORT/IMPORT
    # ========================================
    
    def to_trailing_dict(self):
        """
        Export all trailing session data as dictionary
        
        Returns:
            dict: All trailing session field values
        """
        return {
            # Session info
            't_date': self.t_date.get(),
            't_session_number': self.t_session.get(),
            't_handler': self.t_handler.get(),
            't_dog_name': self.t_dog.get(),
            't_field_support': self.t_field_support.get(),
            
            # Trail details
            't_location': self.t_location.get(),
            't_start_time': self.t_start_time.get(),
            't_finish_time': self.t_finish_time.get(),
            't_trail_age': self.t_trail_age.get(),
            't_trail_length': self.t_trail_length.get(),
            't_difficulty': self.t_difficulty.get(),
            't_trail_layer': self.t_trail_layer.get(),
            't_cross_track_layer': self.t_cross_track_layer.get(),
            't_cross_track_age': self.t_cross_track_age.get(),
            
            # Weather laying
            't_weather_laying': self.t_weather_laying.get(),
            't_temperature_laying': self.t_temp_laying.get(),
            't_wind_speed_laying': self.t_wind_laying.get(),
            't_wind_direction_laying': self.t_wind_direction_laying.get(),
            't_humidity_laying': self.t_humidity_laying.get(),
            
            # Weather running
            't_weather_running': self.t_weather_running.get(),
            't_temperature_running': self.t_temp_running.get(),
            't_wind_speed_running': self.t_wind_running.get(),
            't_wind_direction_running': self.t_wind_direction_running.get(),
            't_humidity_running': self.t_humidity_running.get(),
            
            # Behavior
            't_start_behavior': self.t_start_behavior.get(),
            't_consistency': self.t_consistency.get(),
            't_head_position': self.t_head_pos.get(),
            't_pace': self.t_pace.get(),
            't_indication': self.t_indication.get(),
            't_time_to_complete': self.t_time.get(),
            't_success_rate': self.t_success.get(),
            
            # Impression
            't_impression': self.t_impression.get(),
            
            # Lists
            't_purpose_list': self.t_purpose_list.copy(),
            't_terrain_list': self.t_terrain_list.copy(),
            't_distractions_list': self.t_distractions_list.copy(),
            't_map_files': self.t_map_files_list.copy(),
        }
    
    def from_trailing_dict(self, data):
        """
        Import trailing session data from dictionary
        
        Args:
            data: Dictionary with trailing session field values
        """
        # Session info
        self.t_date.set(data.get('t_date', ''))
        self.t_session.set(str(data.get('t_session_number', '')))
        self.t_handler.set(data.get('t_handler', ''))
        self.t_dog.set(data.get('t_dog_name', ''))
        self.t_field_support.set(data.get('t_field_support', ''))
        
        # Trail details
        self.t_location.set(data.get('t_location', ''))
        self.t_start_time.set(data.get('t_start_time', ''))
        self.t_finish_time.set(data.get('t_finish_time', ''))
        self.t_trail_age.set(data.get('t_trail_age', ''))
        self.t_trail_length.set(data.get('t_trail_length', ''))
        self.t_difficulty.set(data.get('t_difficulty', ''))
        self.t_trail_layer.set(data.get('t_trail_layer', ''))
        self.t_cross_track_layer.set(data.get('t_cross_track_layer', 'None'))
        self.t_cross_track_age.set(data.get('t_cross_track_age', ''))
        
        # Weather laying
        self.t_weather_laying.set(data.get('t_weather_laying', ''))
        self.t_temp_laying.set(data.get('t_temperature_laying', ''))
        self.t_wind_laying.set(data.get('t_wind_speed_laying', ''))
        self.t_wind_direction_laying.set(data.get('t_wind_direction_laying', ''))
        self.t_humidity_laying.set(data.get('t_humidity_laying', ''))
        
        # Weather running
        self.t_weather_running.set(data.get('t_weather_running', ''))
        self.t_temp_running.set(data.get('t_temperature_running', ''))
        self.t_wind_running.set(data.get('t_wind_speed_running', ''))
        self.t_wind_direction_running.set(data.get('t_wind_direction_running', ''))
        self.t_humidity_running.set(data.get('t_humidity_running', ''))
        
        # Behavior
        self.t_start_behavior.set(data.get('t_start_behavior', ''))
        self.t_consistency.set(data.get('t_consistency', ''))
        self.t_head_pos.set(data.get('t_head_position', ''))
        self.t_pace.set(data.get('t_pace', ''))
        self.t_indication.set(data.get('t_indication', ''))
        self.t_time.set(data.get('t_time_to_complete', ''))
        self.t_success.set(data.get('t_success_rate', ''))
        
        # Impression
        self.t_impression.set(data.get('t_impression', ''))
        
        # Lists
        self.t_purpose_list = data.get('t_purpose_list', []).copy()
        self.t_terrain_list = data.get('t_terrain_list', []).copy()
        self.t_distractions_list = data.get('t_distractions_list', []).copy()
        self.t_map_files_list = data.get('t_map_files', []).copy()
    
    # ========================================
    # VALIDATION METHODS
    # ========================================
    
    def validate_session_data(self):
        """
        Validate that required session fields are filled
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.date.get():
            return False, "Date is required"
        
        if not self.session_number.get():
            return False, "Session number is required"
        
        try:
            session_num = int(self.session_number.get())
            if session_num < 1:
                return False, "Session number must be at least 1"
        except ValueError:
            return False, "Session number must be a valid number"
        
        if not self.dog.get():
            return False, "Dog name is required"
        
        return True, ""
    
    def validate_trailing_session_data(self):
        """
        Validate that required trailing session fields are filled
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.t_date.get():
            return False, "Date is required"
        
        if not self.t_session.get():
            return False, "Session number is required"
        
        try:
            session_num = int(self.t_session.get())
            if session_num < 1:
                return False, "Session number must be at least 1"
        except ValueError:
            return False, "Session number must be a valid number"
        
        if not self.t_dog.get():
            return False, "Dog name is required"
        
        return True, ""
    
    # ========================================
    # COMPARISON METHODS
    # ========================================
    
    def get_state_string(self):
        """
        Get string representation of current state for comparison
        
        Returns:
            str: Pipe-separated values for change detection
        """
        data = self.to_dict()
        parts = [str(data.get(key, '')) for key in sorted(data.keys())]
        return "|".join(parts)
    
    def has_changes_from(self, snapshot):
        """
        Check if current state differs from snapshot
        
        Args:
            snapshot: Previously saved state string from get_state_string()
        
        Returns:
            bool: True if state has changed
        """
        return self.get_state_string() != snapshot
    
    def get_trailing_state_string(self):
        """
        Get string representation of current trailing state for comparison
        
        Returns:
            str: Pipe-separated values for change detection
        """
        data = self.to_trailing_dict()
        parts = [str(data.get(key, '')) for key in sorted(data.keys())]
        return "|".join(parts)
    
    def has_trailing_changes_from(self, snapshot):
        """
        Check if current trailing state differs from snapshot
        
        Args:
            snapshot: Previously saved state string from get_trailing_state_string()
        
        Returns:
            bool: True if state has changed
        """
        return self.get_trailing_state_string() != snapshot
    
    # ========================================
    # CONFIGURATION METHODS
    # ========================================
    
    def get_config_dict(self):
        """
        Export configuration-related values
        
        Returns:
            dict: Configuration values
        """
        return {
            'db_type': self.db_type.get(),
            'db_path': self.db_path.get(),
            'trail_maps_folder': self.trail_maps_folder.get(),
            'backup_folder': self.backup_folder.get(),
            'pdf_folder': self.pdf_folder.get(),
            'default_handler': self.default_handler.get(),
        }
    
    def set_config_from_dict(self, config):
        """
        Import configuration values from dictionary
        
        Args:
            config: Dictionary with configuration values
        """
        self.db_type.set(config.get('db_type', 'sqlite'))
        self.db_path.set(config.get('db_path', ''))
        self.trail_maps_folder.set(config.get('trail_maps_folder', ''))
        self.backup_folder.set(config.get('backup_folder', ''))
        self.pdf_folder.set(config.get('pdf_folder', ''))
        self.default_handler.set(config.get('default_handler', ''))


# ========================================
# GLOBAL INSTANCE
# ========================================

# Global sv variable - initialized AFTER Tkinter root window is created
# Usage in ui.py:
#   self.root = TkinterDnD.Tk()
#   sv.initialize(self.root)
sv = None

# Global status bar manager - set by the main UI after StatusBarManager is created
# This allows any module to call show_status_message() without needing a UI reference
_status_bar_mgr = None


def set_status_bar_manager(mgr):
    """
    Set the global status bar manager reference.
    Called by the main UI after creating the StatusBarManager.
    
    Args:
        mgr: The StatusBarManager instance
    """
    global _status_bar_mgr
    _status_bar_mgr = mgr


def show_status_message(message, msg_type="info"):
    """
    Display a status message using the global StatusBarManager.
    Can be called from any module after the UI is initialized.
    
    Args:
        message: Message text to display
        msg_type: "info", "warning", or "error"
    
    Falls back to sv.status.set() if StatusBarManager not yet initialized.
    """
    global _status_bar_mgr, sv
    
    if _status_bar_mgr is not None:
        _status_bar_mgr.show_message(message, msg_type)
    elif sv is not None:
        # Fallback to direct StringVar set if StatusBarManager not ready
        sv.status.set(message)


def initialize(master=None):
    """
    Initialize the global sv instance with the Tkinter root window
    
    Must be called after creating the Tkinter root window:
        root = tk.Tk()
        initialize(root)
    
    Args:
        master: The Tkinter root window
        
    Returns:
        The initialized sv instance
    """
    global sv
    if sv is None:
        sv = Stringvars(master=master)
    return sv


# ========================================
# CONVENIENCE FUNCTIONS
# ========================================

def reset_all(master=None):
    """Reset global sv to fresh instance (useful for testing)"""
    global sv
    sv = Stringvars(master=master)


def get_session_data():
    """Convenience function to get session data dictionary"""
    if sv is None:
        raise RuntimeError("sv not initialized. Call initialize(root) first.")
    return sv.to_dict()


def __getattr__(name):
    """
    Allow accessing sv instance attributes directly from module
    
    This allows: sv.date.get() instead of sv.sv.date.get()
    Works by forwarding attribute access to the sv instance.
    """
    if sv is None:
        raise RuntimeError(f"sv not initialized. Call initialize(root) before accessing {name}")
    return getattr(sv, name)


def load_session_data(data):
    """Convenience function to load session data from dictionary"""
    sv.from_dict(data)


def clear_form(keep_handler=True, keep_dog=True):
    """Convenience function to clear form fields"""
    sv.clear_session_fields(keep_handler=keep_handler, keep_dog=keep_dog)


# ========================================
# EXAMPLE USAGE
# ========================================

if __name__ == "__main__":
    # Example 1: Direct access
    print("Example 1: Direct access")
    sv.date.set("2025-01-15")
    sv.handler.set("John Smith")
    sv.dog.set("Rover")
    print(f"Date: {sv.date.get()}")
    print(f"Handler: {sv.handler.get()}")
    print(f"Dog: {sv.dog.get()}")
    
    # Example 2: Export to dictionary
    print("\nExample 2: Export to dictionary")
    data = sv.to_dict()
    print(f"Session data: {data}")
    
    # Example 3: Clear fields
    print("\nExample 3: Clear fields")
    sv.clear_session_fields(keep_handler=True, keep_dog=False)
    print(f"After clear - Handler: {sv.handler.get()}")
    print(f"After clear - Dog: {sv.dog.get()}")
    
    # Example 4: Validation
    print("\nExample 4: Validation")
    sv.session_number.set("5")
    is_valid, error = sv.validate_session_data()
    print(f"Valid: {is_valid}, Error: {error}")
    
    # Example 5: Change detection
    print("\nExample 5: Change detection")
    snapshot = sv.get_state_string()
    sv.temperature.set("72ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â°F")
    has_changes = sv.has_changes_from(snapshot)
    print(f"Has changes: {has_changes}")
    
    print("\nAll examples completed successfully!")
