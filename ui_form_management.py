"""
Form Management Module for Air-Scenting Logger
Handles form clearing, loading, validation, and state tracking
"""
from datetime import datetime
from tkinter import messagebox


class FormManagement:
    """Manages form state, validation, and operations"""
    
    def __init__(self, ui):
        """
        Initialize with reference to main UI
        
        Args:
            ui: Reference to AirScentingUI instance
        """
        self.ui = ui
        self.form_snapshot = ""  # Stores snapshot of form state for change detection
    
    # ========================================
    # FORM STATE MANAGEMENT
    # ========================================
    
    def take_form_snapshot(self):
        """Take a snapshot of the current form state"""
        self.form_snapshot = self.get_form_state_string()
    
    def get_form_state_string(self):
        """Get a string representation of all form fields for comparison"""
        from sv import sv
        
        parts = [
            sv.db_type.get(),
            sv.db_path.get(),
            sv.trail_maps_folder.get(),
            sv.backup_folder.get(),
            sv.default_handler.get(),
            # Include entry widget values (in case user typed but didn't click Add)
            sv.new_location.get(),
            sv.new_dog.get(),
            sv.new_terrain.get(),
            sv.new_distraction.get(),
            # Include lists from config
            ", ".join(sorted(self.ui.config.get("training_locations", []))),
            ", ".join(self.ui.config.get("terrain_types", [])),
            ", ".join(self.ui.config.get("distraction_types", []))
        ]
        return "|".join(parts)
    
    def has_unsaved_changes(self):
        """Check if the form has unsaved changes"""
        current_state = self.get_form_state_string()
        return current_state != self.form_snapshot
    
    def check_unsaved_changes(self, action_name="proceed"):
        """
        Check for unsaved changes and prompt user. Returns True if OK to proceed.
        
        Args:
            action_name: Description of action about to be taken (for prompt)
        
        Returns:
            bool: True if OK to proceed, False if user cancelled
        """
        if not self.has_unsaved_changes():
            return True
        
        # Prompt user
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            f"You have unsaved changes.\n\nDo you want to save before you {action_name}?",
            icon='warning'
        )
        
        if result is None:  # Cancel
            return False
        elif result:  # Yes - save first
            # Import here to avoid circular dependency
            from ui_setup_tab import SetupTab
            setup = SetupTab(self.ui)
            setup.save_configuration_settings()
            return True
        else:  # No - discard changes
            return True
    
    def check_entry_tab_changes(self):
        """Check for unsaved changes in Entry tab. Returns True if OK to proceed."""
        from sv import sv
        from ui_database import DatabaseOperations
        import tkinter as tk
        import json
        
        # Get current form state
        current_date = sv.date.get()
        current_session = sv.session_number.get()
        current_handler = sv.handler.get()
        current_purpose = sv.session_purpose.get()
        current_field_support = sv.field_support.get()
        current_dog = sv.dog.get()
        current_location = sv.location.get()
        current_search_area = sv.search_area_size.get()
        current_num_subjects = sv.num_subjects.get()
        current_handler_knowledge = sv.handler_knowledge.get()
        current_weather = sv.weather.get()
        current_temperature = sv.temperature.get()
        current_wind_direction = sv.wind_direction.get()
        current_wind_speed = sv.wind_speed.get()
        current_search_type = sv.search_type.get()
        current_drive_level = sv.drive_level.get()
        current_subjects_found = sv.subjects_found.get()
        current_comments = self.ui.comments_text.get("1.0", tk.END).strip()
        
        # Check if this session exists in database and compare
        try:
            session_num = int(current_session)
        except ValueError:
            return True  # Invalid session number, OK to proceed
        
        db_type = sv.db_type.get()
        
        try:
            # Get data from database using get_session_with_related_data
            db_ops = DatabaseOperations(self.ui)
            session_dict = db_ops.get_session_with_related_data(session_num, current_dog)
            
            if session_dict:
                # Compare basic fields (handle empty strings vs None)
                def safe_str(val):
                    """Convert to string, treating None and empty string as equivalent"""
                    return str(val) if val is not None else ""
                
                # Compare basic fields
                if (safe_str(current_date) != safe_str(session_dict.get("date")) or
                    safe_str(current_handler) != safe_str(session_dict.get("handler")) or
                    safe_str(current_purpose) != safe_str(session_dict.get("session_purpose")) or
                    safe_str(current_field_support) != safe_str(session_dict.get("field_support")) or
                    safe_str(current_dog) != safe_str(session_dict.get("dog_name")) or
                    safe_str(current_location) != safe_str(session_dict.get("location")) or
                    safe_str(current_search_area) != safe_str(session_dict.get("search_area_size")) or
                    safe_str(current_num_subjects) != safe_str(session_dict.get("num_subjects")) or
                    safe_str(current_handler_knowledge) != safe_str(session_dict.get("handler_knowledge")) or
                    safe_str(current_weather) != safe_str(session_dict.get("weather")) or
                    safe_str(current_temperature) != safe_str(session_dict.get("temperature")) or
                    safe_str(current_wind_direction) != safe_str(session_dict.get("wind_direction")) or
                    safe_str(current_wind_speed) != safe_str(session_dict.get("wind_speed")) or
                    safe_str(current_search_type) != safe_str(session_dict.get("search_type")) or
                    safe_str(current_drive_level) != safe_str(session_dict.get("drive_level")) or
                    safe_str(current_subjects_found) != safe_str(session_dict.get("subjects_found")) or
                    safe_str(current_comments) != safe_str(session_dict.get("comments"))):
                    
                    # Changes detected in basic fields
                    result = messagebox.askyesnocancel(
                        "Unsaved Changes",
                        f"You have unsaved changes to Session #{session_num}.\n\n"
                        "Do you want to save before proceeding?",
                        icon='warning'
                    )
                    
                    if result is None:  # Cancel
                        return False
                    elif result:  # Yes - save first
                        from ui_entry_tab import EntryTab
                        entry = EntryTab(self.ui)
                        entry.save_session()
                        return True
                    else:  # No - discard changes
                        return True
                
                # Compare selected terrains
                db_terrains = set(session_dict.get("selected_terrains", []))
                current_terrains = set(self.ui.accumulated_terrains)
                
                if db_terrains != current_terrains:
                    result = messagebox.askyesnocancel(
                        "Unsaved Changes",
                        f"You have unsaved terrain changes to Session #{session_num}.\n\n"
                        "Do you want to save before proceeding?",
                        icon='warning'
                    )
                    
                    if result is None:
                        return False
                    elif result:
                        from ui_entry_tab import EntryTab
                        entry = EntryTab(self.ui)
                        entry.save_session()
                        return True
                    else:
                        return True
                
                # Compare subject responses
                db_responses = session_dict.get("subject_responses", [])
                db_responses_dict = {r["subject_number"]: (r["tfr"], r["refind"]) for r in db_responses}
                
                current_responses_dict = {}
                for i in range(1, 11):
                    item_id = f'subject_{i}'
                    tags = self.ui.subject_responses_tree.item(item_id, 'tags')
                    if 'enabled' in tags:
                        values = self.ui.subject_responses_tree.item(item_id, 'values')
                        tfr = values[1] if len(values) > 1 else ''
                        refind = values[2] if len(values) > 2 else ''
                        current_responses_dict[i] = (tfr, refind)
                
                if db_responses_dict != current_responses_dict:
                    result = messagebox.askyesnocancel(
                        "Unsaved Changes",
                        f"You have unsaved subject response changes to Session #{session_num}.\n\n"
                        "Do you want to save before proceeding?",
                        icon='warning'
                    )
                    
                    if result is None:
                        return False
                    elif result:
                        from ui_entry_tab import EntryTab
                        entry = EntryTab(self.ui)
                        entry.save_session()
                        return True
                    else:
                        return True
            
            # No changes or new session
            return True
            
        except Exception as e:
            # If error checking, just proceed
            print(f"Error in check_entry_tab_changes: {e}")
            return True
    
    def clear_form(self):
        """Clear the form"""
        from sv import sv
        import tkinter as tk
        
        result = messagebox.askyesno("Clear Form", "Are you sure you want to clear all fields?")
        if result:
            sv.date.set(datetime.now().strftime("%Y-%m-%d"))
            
            # Get next session number
            from ui_database import DatabaseOperations
            db_ops = DatabaseOperations(self.ui)
            sv.session_number.set(str(db_ops.get_next_session_number()))
            
            # handler is NOT cleared - keep current handler name
            sv.session_purpose.set("")
            sv.field_support.set("")
            # dog is NOT cleared - keep current dog (persists)
            sv.location.set("")
            sv.search_area_size.set("")
            sv.num_subjects.set("")
            sv.handler_knowledge.set("")
            sv.weather.set("")
            sv.temperature.set("")
            sv.wind_direction.set("")
            sv.wind_speed.set("")
            sv.search_type.set("")
            sv.drive_level.set("")
            sv.subjects_found.set("")
            
            # Clear comments textbox
            self.ui.comments_text.delete("1.0", tk.END)
            
            # Clear map files list
            self.ui.map_files_list = []
            self.ui.map_listbox.delete(0, tk.END)
            self.ui.view_map_button.config(state=tk.DISABLED)
            self.ui.delete_map_button.config(state=tk.DISABLED)
            
            # Clear selected terrains
            self.ui.accumulated_terrains = []
            if hasattr(self.ui, 'accumulated_terrain_combo'):
                self.ui.accumulated_terrain_combo['values'] = []
                sv.accumulated_terrain.set("")
            
            # Clear subject responses tree
            for i in range(1, 11):
                item_id = f'subject_{i}'
                if self.ui.subject_responses_tree.exists(item_id):
                    self.ui.subject_responses_tree.item(item_id, tags='disabled')
                    self.ui.subject_responses_tree.item(item_id, values=(
                        f'Subject {i}', '', ''
                    ))
            
            # Update subjects_found combo state (will disable since num_subjects is blank)
            self.update_subjects_found()
            
            sv.status.set("Form cleared")
            
            # Update navigation buttons
            from ui_navigation import Navigation
            nav = Navigation(self.ui)
            nav.update_navigation_buttons()
    
    def new_session(self):
        """Advance to first available new session (MAX + 1)"""
        from sv import sv
        from ui_database import DatabaseOperations
        from ui_navigation import Navigation
        import tkinter as tk
        
        # Check for unsaved changes first
        if not self.check_entry_tab_changes():
            return
        
        db_ops = DatabaseOperations(self.ui)
        next_session = db_ops.get_next_session_number()
        sv.session_number.set(str(next_session))
        
        # Clear selected sessions - we're starting fresh
        self.ui.selected_sessions = []
        self.ui.selected_sessions_index = -1
        
        # Clear form fields for new entry (KEEP handler name and dog name)
        self.ui.set_date(datetime.now().strftime("%Y-%m-%d"))
        # handler is NOT cleared - keep current handler name
        sv.session_purpose.set("")
        sv.field_support.set("")
        # dog is NOT cleared - keep current dog (persists across sessions)
        sv.location.set("")
        sv.search_area_size.set("")
        sv.num_subjects.set("")
        sv.handler_knowledge.set("")
        sv.weather.set("")
        sv.temperature.set("")
        sv.wind_direction.set("")
        sv.wind_speed.set("")
        sv.search_type.set("")
        sv.drive_level.set("")
        sv.subjects_found.set("")
        
        # Clear map files list
        self.ui.map_files_list = []
        self.ui.map_listbox.delete(0, "end")
        self.ui.view_map_button.config(state="disabled")
        self.ui.delete_map_button.config(state="disabled")
        
        # Clear comments textbox
        self.ui.comments_text.delete("1.0", tk.END)
        
        # Clear map files list (already present but adding comments/terrains)
        
        # Clear selected terrains
        self.ui.accumulated_terrains = []
        if hasattr(self.ui, 'accumulated_terrain_combo'):
            self.ui.accumulated_terrain_combo['values'] = []
            sv.accumulated_terrain.set("")
        
        # Clear subject responses tree
        for i in range(1, 11):
            item_id = f'subject_{i}'
            if self.ui.subject_responses_tree.exists(item_id):
                self.ui.subject_responses_tree.item(item_id, tags='disabled')
                self.ui.subject_responses_tree.item(item_id, values=(
                    f'Subject {i}', '', ''
                ))
        
        # Update subjects_found combo state (will disable since num_subjects is blank)
        self.update_subjects_found()
        
        sv.status.set(f"New session #{next_session}")
        
        # Update navigation buttons
        nav = Navigation(self.ui)
        nav.update_navigation_buttons()
    
    # ========================================
    # FORM FIELD UPDATES
    # ========================================
    
    def update_subjects_found(self, event=None):
        """Update Subjects Found combobox values based on Number of Subjects"""
        from sv import sv
        
        num_subjects = sv.num_subjects.get()
        
        if num_subjects and num_subjects.isdigit():
            n = int(num_subjects)
            # Generate values: "0 out of n", "1 out of n", ..., "n out of n"
            values = [f"{i} out of {n}" for i in range(n + 1)]
            self.ui.subjects_found_combo['values'] = values
            self.ui.subjects_found_combo['state'] = 'readonly'
            # Clear current selection when choices change
            sv.subjects_found.set("")
        else:
            # No number selected, disable and clear the subjects_found combobox
            self.ui.subjects_found_combo['values'] = []
            self.ui.subjects_found_combo['state'] = 'disabled'
            sv.subjects_found.set("")
