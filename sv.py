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
        self.session_purpose = tk.StringVar(master=master)
        self.field_support = tk.StringVar(master=master)
        
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
        
        # ===== TERRAIN (List of selected terrains) =====
        # Note: This is a list, not StringVar, to hold multiple selections
        self.terrain_list = []  
        
        # ===== SUBJECT RESPONSES (List of dicts) =====
        # Note: This holds structured data for subject responses
        self.subject_responses = []
        
        # ===== SETUP TAB - PATHS =====
        self.db_path = tk.StringVar(master=master)
        self.trail_maps_folder = tk.StringVar(master=master)
        self.backup_folder = tk.StringVar(master=master)
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
        
        # Terrain and subject responses
        self.terrain_list.clear()
        self.subject_responses.clear()
    
    def clear_setup_entry_fields(self):
        """Clear all entry fields on setup tab"""
        self.new_location.set("")
        self.new_dog.set("")
        self.new_terrain.set("")
        self.new_distraction.set("")
    
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
        
        # Terrain (list)
        self.terrain_list = data.get('terrain_list', []).copy()
        
        # Subject responses (list of dicts)
        self.subject_responses = data.get('subject_responses', []).copy()
    
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
        self.default_handler.set(config.get('default_handler', ''))


# ========================================
# GLOBAL INSTANCE
# ========================================

# Global sv variable - initialized AFTER Tkinter root window is created
# Usage in ui.py:
#   self.root = TkinterDnD.Tk()
#   sv.initialize(self.root)
sv = None


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
    sv.temperature.set("72°F")
    has_changes = sv.has_changes_from(snapshot)
    print(f"Has changes: {has_changes}")
    
    print("\nAll examples completed successfully!")
