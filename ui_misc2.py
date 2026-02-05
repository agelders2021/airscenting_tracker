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
                
                # Update session number to next computed number for this dog (Airscent sessions only)
                status_filter = sv.session_status_filter.get()
                filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(
                    dog_name, status_filter, entry_type="Airscent"
                )
                next_computed = len(filtered_sessions) + 1
                sv.session_number.set(str(next_computed))
                print(f"DEBUG on_dog_changed: set to computed {next_computed}")  # DEBUG
                
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
                sv.start_time.set("")
                sv.finish_time.set("")
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
                
                sv.status.set(f"Switched to {dog_name} - Next session: #{next_computed}")
                
            finally:
                if working_dialog:
                    working_dialog.close(delay_ms=200)  # 200ms delay for UI to update
    def save_session(self):
        from sv import sv
        """Save the current training session"""
        # Get all form values
        date = self.ui.a_date_picker.get_date().strftime("%Y-%m-%d")
        displayed_session_number = sv.session_number.get()
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
        start_time = sv.start_time.get()
        finish_time = sv.finish_time.get()
        comments = self.ui.a_comments_text.get("1.0", tk.END).strip()

        # Map/image files - store as JSON string
        image_files_json = json.dumps(self.ui.map_files_list) if self.ui.map_files_list else ""

        # Validate required fields
        if not date:
            messagebox.showwarning("Missing Data", "Please enter a date")
            return
        if not displayed_session_number:
            messagebox.showwarning("Missing Data", "Please enter a session number")
            return
        if not dog_name:
            messagebox.showwarning("Missing Data", "Please select a dog")
            return

        try:
            displayed_session_number = int(displayed_session_number)
        except ValueError:
            messagebox.showwarning("Invalid Data", "Session number must be a number")
            return

        # Determine if we're in UPDATE mode or NEW mode
        # UPDATE mode: We're editing an existing session (selected_sessions is set, or current_db_session_number is set)
        # NEW mode: We're creating a brand new session
        
        is_update_mode = False
        db_session_number = None
        
        # Check if we're viewing/editing a selected session
        if self.ui.selected_sessions:
            is_update_mode = True
            from ui_navigation import Navigation
            nav = Navigation(self.ui)
            db_session_number = nav.get_current_db_session_number()
            print(f"DEBUG save_session: Update mode (selected_sessions), db_session_number={db_session_number}")
        
        # Also check current_db_session_number - if it's set, we might be in update mode
        elif hasattr(self.ui, 'current_db_session_number') and self.ui.current_db_session_number is not None:
            # We have a current session loaded - check if it actually exists in DB
            db_ops = DatabaseOperations(self.ui)
            existing_session = db_ops.get_session_with_related_data(self.ui.current_db_session_number, dog_name)
            if existing_session:
                is_update_mode = True
                db_session_number = self.ui.current_db_session_number
                print(f"DEBUG save_session: Update mode (current_db_session_number), db_session_number={db_session_number}")
        
        # Determine the actual session_number to save to database
        if is_update_mode and db_session_number:
            # UPDATE MODE: Use the database session number
            session_number = db_session_number
            print(f"DEBUG save_session: Using db_session_number={session_number} for UPDATE")
        else:
            # NEW MODE: Get the actual next session number from database (MAX + 1)
            # This prevents collision with deleted sessions
            db_ops = DatabaseOperations(self.ui)
            session_number = db_ops.get_next_session_number(dog_name)
            print(f"DEBUG save_session: NEW mode - using next DB session number={session_number} (displayed was {displayed_session_number})")
        
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
            "start_time": start_time,
            "finish_time": finish_time,
            "comments": comments,
            "image_files": image_files_json,
            "entry_type": "Airscent"  # Identifies this as an air-scenting session
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
            success, message, session_id, session_uuid, update_time = db_mgr.save_session(session_data)

            if not success:
                messagebox.showerror("Database Error", message)
                return

            # Save selected terrains
            db_mgr.save_selected_terrains(session_id, self.ui.accumulated_terrains)

            # Save selected purposes
            selected_purposes = self.ui.get_selected_purposes()
            db_mgr.save_selected_purposes(session_id, selected_purposes)

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

        # Save last handler name to nested airscenting config
        if handler:
            if "airscenting" not in self.ui.config:
                self.ui.config["airscenting"] = {}
            self.ui.config["airscenting"]["last_handler"] = handler
            self.ui.save_config()

        # Save session to JSON backup (include uuid and update_time for sync)
        # Get status from session_data or default to 'active'
        session_status = session_data.get("status", "active")
        session_backup_data = {
            **session_data,
            "subject_responses": subject_responses_list,
            "image_files": self.ui.map_files_list,
            "selected_terrains": self.ui.accumulated_terrains,
            "selected_purposes": selected_purposes,
            "user_name": get_username(),
            "uuid": session_uuid,
            "update_time": update_time,
            "status": session_status
        }
        self.ui.misc_data_ops.save_session_to_json(session_backup_data)

        # Save current handler to config for persistence across sessions and restarts
        current_handler = sv.handler.get()
        if current_handler:
            if "airscenting" not in self.ui.config:
                self.ui.config["airscenting"] = {}
            self.ui.config["airscenting"]["default_handler"] = current_handler
            self.ui.save_config()

        # Show success message
        self.ui.show_status_message(message, "info")

        # Handle post-save behavior - always prepare for a new session after save/update
        from ui_navigation import Navigation
        nav = Navigation(self.ui)
        
        if is_update_mode:
            # Get the session status for display message
            db_ops = DatabaseOperations(self.ui)
            saved_status = db_ops.get_session_status(session_data["session_number"], dog_name)
            self.ui.show_status_message(f"Updated session (Status: {saved_status})", "info")
        
        # BOTH NEW AND UPDATE MODE: Clear form and prepare for next entry
        # Clear current_db_session_number to exit any lingering update mode
        self.ui.current_db_session_number = None
        self.ui.selected_sessions = []
        self.ui.selected_sessions_index = -1
        
        # Set to computed next number based on filter for DISPLAY purposes
        # (The actual DB session number will be determined at next save)
        status_filter = sv.session_status_filter.get()
        filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(
            dog_name, status_filter, entry_type="Airscent"
        )
        next_computed = len(filtered_sessions) + 1
        sv.session_number.set(str(next_computed))
        print(f"DEBUG save_session: Prepared for new session, displayed number={next_computed}")

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
        sv.start_time.set("")
        sv.finish_time.set("")
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
        
        # Reset save button text to "Save Session" for new entries
        self.ui.set_save_button_text("Save Session")
        
        # Reset session frame title for new entry
        nav.update_session_frame_title(None)
        
        # Call new_session to properly reset form state (skip change check since we just saved)
        # This ensures the form is in a clean "new session" state with proper snapshot
        self.ui.form_mgmt.new_session(skip_change_check=True)


