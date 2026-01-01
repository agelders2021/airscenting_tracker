"""
UI Miscellaneous Operations Part 2
Extracted from ui.py for better organization
Contains dog-related and other miscellaneous operations
"""
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from ui_database import DatabaseOperations, get_db_manager
from ui_utils import get_username
import json
import os
from pathlib import Path
from working_dialog import WorkingDialog
# from sv import sv


class Misc2Operations:
    """Handles miscellaneous UI operations - part 2"""
    
    def __init__(self, ui):
        """Initialize with reference to main UI instance"""
        self.ui = ui
    
    def on_dog_changed(self, event=None):
        from sv import sv
        """Called when dog selection changes - update session number and clear form for new dog"""
        dog_name = sv.dog.get()
        # print(f"DEBUG on_dog_changed: dog_name = '{dog_name}'")  # DEBUG
        if dog_name:
            db_type = sv.db_type.get()
            
            # Show working dialog for networked databases
            if db_type in ["postgres", "supabase", "mysql"]:
                working_dialog = WorkingDialog(self.ui.root, "Loading Dog Data", 
                                             f"Loading data for {dog_name}...")
                self.ui.root.update()
            else:
                working_dialog = None
            
            try:
                # Save dog to database for persistence across sessions
                DatabaseOperations(self.ui).save_db_setting("last_dog_name", dog_name)
                
                # Update session number to next available for this dog
                next_session = DatabaseOperations(self.ui).get_next_session_number(dog_name)
                # print(f"DEBUG on_dog_changed: next_session = {next_session}")  # DEBUG
                sv.session_number.set(str(next_session))
                
                # Clear form fields for new dog (like "New" button but keep handler and dog)
                self.ui.set_date(datetime.now().strftime("%Y-%m-%d"))
                # handler_var is NOT cleared - keep current handler name
                sv.session_purpose.set("")
                sv.field_support.set("")
                # dog_var is already set - don't clear it
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
                self.ui.a_comments_text.delete("1.0", tk.END)
                # Clear terrain accumulator
                self.ui.accumulated_terrains = []
                self.ui.a_accumulated_terrain_combo['values'] = []
                sv.accumulated_terrain.set("")
                self.ui.a_accumulated_terrain_combo['state'] = 'disabled'  # Disable when cleared
                # Clear map files list
                self.ui.map_files_list = []
                self.ui.a_map_listbox.delete(0, tk.END)
                self.ui.a_view_map_button.config(state=tk.DISABLED)
                self.ui.a_delete_map_button.config(state=tk.DISABLED)
                # Update subjects_found combo state
                self.ui.form_mgmt.update_subjects_found()
                
                # Clear selected sessions - switching dogs exits navigation mode
                self.ui.selected_sessions = []
                self.ui.selected_sessions_index = -1
                
                # Update navigation buttons
                self.ui.navigation.update_navigation_buttons()
                
                sv.status.set(f"Switched to {dog_name} - Next session: #{next_session}")
                
            finally:
                if working_dialog:
                    working_dialog.close(delay_ms=200)  # 200ms delay for UI to update
    def save_session(self):
        from sv import sv
        """Save the current training session"""
        # Get all form values
        date = self.ui.a_date_picker.get_date().strftime("%Y-%m-%d")
        session_number = sv.session_number.get()
        handler = sv.handler.get()
        session_purpose = sv.session_purpose.get()
        field_support = sv.field_support.get()
        dog_name = sv.dog.get().strip() if sv.dog.get() else ""

        # Search parameters
        location = sv.location.get()
        search_area_size = sv.search_area_size.get()
        num_subjects = sv.num_subjects.get()
        handler_knowledge = sv.handler_knowledge.get()
        weather = sv.weather.get()
        temperature = sv.temperature.get()
        wind_direction = sv.wind_direction.get()
        wind_speed = sv.wind_speed.get()
        search_type = sv.search_type.get()

        # Search results
        drive_level = sv.drive_level.get()
        subjects_found = sv.subjects_found.get()
        comments = self.ui.a_comments_text.get("1.0", tk.END).strip()

        # Map/image files - store as JSON string
        image_files_json = json.dumps(self.ui.map_files_list) if self.ui.map_files_list else ""

        # Validate required fields
        if not date:
            messagebox.showwarning("Missing Data", "Please enter a date")
            return
        if not session_number:
            messagebox.showwarning("Missing Data", "Please enter a session number")
            return
        if not dog_name:
            messagebox.showwarning("Missing Data", "Please select a dog")
            return

        try:
            session_number = int(session_number)
        except ValueError:
            messagebox.showwarning("Invalid Data", "Session number must be a number")
            return

        # Prepare session data dict
        session_data = {
            "date": date,
            "session_number": session_number,
            "handler": handler,
            "session_purpose": session_purpose,
            "field_support": field_support,
            "dog_name": dog_name,
            "location": location,
            "search_area_size": search_area_size,
            "num_subjects": num_subjects,
            "handler_knowledge": handler_knowledge,
            "weather": weather,
            "temperature": temperature,
            "wind_direction": wind_direction,
            "wind_speed": wind_speed,
            "search_type": search_type,
            "drive_level": drive_level,
            "subjects_found": subjects_found,
            "comments": comments,
            "image_files": image_files_json
        }

        # Save to database using DatabaseManager
        db_mgr = get_db_manager(sv.db_type.get())
        
        # Show working dialog for networked databases
        db_type = sv.db_type.get()
        if db_type in ["postgres", "supabase", "mysql"]:
            working_dialog = WorkingDialog(self.ui.root, "Saving", 
                                         f"Saving session to {db_type} database...")
            self.ui.root.update()
        else:
            working_dialog = None
        
        try:
            success, message, session_id = db_mgr.save_session(session_data)

            if not success:
                messagebox.showerror("Database Error", message)
                return

            # Save selected terrains
            db_mgr.save_selected_terrains(session_id, self.ui.accumulated_terrains)

            # Save subject responses
            subject_responses_list = []
            for i in range(1, 11):
                item_id = f'subject_{i}'
                tags = self.ui.a_subject_responses_tree.item(item_id, 'tags')

                if 'enabled' in tags:
                    values = self.ui.a_subject_responses_tree.item(item_id, 'values')
                    subject_responses_list.append({
                        "subject_number": i,
                        "tfr": values[1] if len(values) > 1 else '',
                        "refind": values[2] if len(values) > 2 else ''
                    })

            db_mgr.save_subject_responses(session_id, subject_responses_list)
        finally:
            if working_dialog:
                working_dialog.close(delay_ms=200)

        # Save last handler name to config
        if handler:
            self.ui.config["last_handler_name"] = handler
            self.ui.save_config()

        # Save session to JSON backup
        session_backup_data = {
            **session_data,
            "subject_responses": subject_responses_list,
            "image_files": self.ui.map_files_list,
            "selected_terrains": self.ui.accumulated_terrains,
            "user_name": get_username()
        }
        self.ui.misc_data_ops.save_session_to_json(session_backup_data)

        sv.status.set(message)
        messagebox.showinfo("Success", message)

        # Auto-prepare for next entry
        sv.session_number.set(str(DatabaseOperations(self).get_next_session_number()))
        self.ui.selected_sessions = []
        self.ui.selected_sessions_index = -1

        # Clear form fields (keep handler and dog)
        self.ui.set_date(datetime.now().strftime("%Y-%m-%d"))
        sv.session_purpose.set("")
        sv.field_support.set("")
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
        self.ui.a_comments_text.delete("1.0", tk.END)
        self.ui.accumulated_terrains = []
        self.ui.a_accumulated_terrain_combo['values'] = []
        sv.accumulated_terrain.set("")
        self.ui.a_accumulated_terrain_combo['state'] = 'disabled'  # Disable when cleared
        self.ui.map_files_list = []
        self.ui.a_map_listbox.delete(0, tk.END)
        self.ui.a_view_map_button.config(state=tk.DISABLED)
        self.ui.a_delete_map_button.config(state=tk.DISABLED)
        self.ui.form_mgmt.update_subjects_found()
        # Clear subject responses tree
        for i in range(1, 11):
            item_id = f'subject_{i}'
            if self.ui.a_subject_responses_tree.exists(item_id):
                self.ui.a_subject_responses_tree.item(item_id, tags='disabled')
                self.ui.a_subject_responses_tree.item(item_id, values=(
                    f'Subject {i}', '', ''
                ))
        
        # Reset tree selection to subject 1 after clearing form
        self.ui.reset_subject_responses_tree_selection()
        self.ui.navigation.update_navigation_buttons()


