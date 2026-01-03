"""
Navigation Module for Air-Scenting Logger
Handles session navigation (Previous/Next), session selection, and loading
"""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime


class Navigation:
    """Manages session navigation and loading"""
    
    def __init__(self, ui):
        """
        Initialize with reference to main UI
        
        Args:
            ui: Reference to AirScentingUI instance
        """
        self.ui = ui
    
    # ========================================
    # NAVIGATION BUTTONS
    # ========================================
    
    def update_navigation_buttons(self):
        """Enable/disable Previous and Next buttons based on current session number"""
        from sv import sv
        from ui_database import DatabaseOperations
        
        # If we have selected sessions, use that for navigation
        if self.ui.selected_sessions:
            # Enable Previous if not at first selected session
            if self.ui.selected_sessions_index > 0:
                self.ui.a_prev_session_btn.config(state="normal")
            else:
                self.ui.a_prev_session_btn.config(state="disabled")
            
            # Enable Next if not at last selected session
            if self.ui.selected_sessions_index < len(self.ui.selected_sessions) - 1:
                self.ui.a_next_session_btn.config(state="normal")
            else:
                self.ui.a_next_session_btn.config(state="disabled")
        else:
            # Normal mode - check filtered session list
            try:
                current_session = int(sv.session_number.get())
                dog_name = sv.dog.get()
                
                if not dog_name:
                    self.ui.a_prev_session_btn.config(state="disabled")
                    self.ui.a_next_session_btn.config(state="disabled")
                    return
                
                # Get filtered sessions for current dog
                db_ops = DatabaseOperations(self.ui)
                status_filter = sv.session_status_filter.get()
                sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
                
                if not sessions:
                    self.ui.a_prev_session_btn.config(state="disabled")
                    self.ui.a_next_session_btn.config(state="disabled")
                    return
                
                # Extract session numbers
                session_numbers = [s[0] for s in sessions]
                
                # Check if current session is in filtered list
                if current_session in session_numbers:
                    current_index = session_numbers.index(current_session)
                    
                    # Enable Previous if not at first filtered session
                    if current_index > 0:
                        self.ui.a_prev_session_btn.config(state="normal")
                    else:
                        self.ui.a_prev_session_btn.config(state="disabled")
                    
                    # Enable Next if not at last filtered session
                    if current_index < len(session_numbers) - 1:
                        self.ui.a_next_session_btn.config(state="normal")
                    else:
                        self.ui.a_next_session_btn.config(state="disabled")
                else:
                    # Current session not in filtered list - disable both
                    self.ui.a_prev_session_btn.config(state="disabled")
                    self.ui.a_next_session_btn.config(state="disabled")
                    
            except ValueError:
                self.ui.a_prev_session_btn.config(state="disabled")
                self.ui.a_next_session_btn.config(state="disabled")
    
    def navigate_previous_session(self):
        """Navigate to previous session"""
        from sv import sv
        
        # If we have selected sessions, navigate through those
        if self.ui.selected_sessions and self.ui.selected_sessions_index > 0:
            self.ui.selected_sessions_index -= 1
            session_num = self.ui.selected_sessions[self.ui.selected_sessions_index]
            sv.session_number.set(str(session_num))
            self.load_session_by_number(session_num)
            self.update_navigation_buttons()
            sv.status.set(
                f"Session {self.ui.selected_sessions_index + 1} of {len(self.ui.selected_sessions)} selected"
            )
        else:
            # Normal navigation - navigate through filtered sessions
            try:
                current = int(sv.session_number.get())
                dog_name = sv.dog.get()
                
                if not dog_name:
                    return
                
                # Get filtered sessions for current dog
                db_ops = DatabaseOperations(self.ui)
                status_filter = sv.session_status_filter.get()
                sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
                
                if not sessions:
                    return
                
                # Extract session numbers from the list of tuples
                session_numbers = [s[0] for s in sessions]
                
                # Find current session in the list
                if current in session_numbers:
                    current_index = session_numbers.index(current)
                    if current_index > 0:  # Can go previous
                        prev_session = session_numbers[current_index - 1]
                        sv.session_number.set(str(prev_session))
                        self.load_session_by_number(prev_session)
                        self.update_navigation_buttons()
                
            except ValueError:
                pass
    
    def navigate_next_session(self):
        """Navigate to next session"""
        from sv import sv
        from ui_database import DatabaseOperations
        
        # If we have selected sessions, navigate through those
        if self.ui.selected_sessions and self.ui.selected_sessions_index < len(self.ui.selected_sessions) - 1:
            self.ui.selected_sessions_index += 1
            session_num = self.ui.selected_sessions[self.ui.selected_sessions_index]
            sv.session_number.set(str(session_num))
            self.load_session_by_number(session_num)
            self.update_navigation_buttons()
            sv.status.set(
                f"Session {self.ui.selected_sessions_index + 1} of {len(self.ui.selected_sessions)} selected"
            )
        else:
            # Normal navigation - navigate through filtered sessions
            try:
                current = int(sv.session_number.get())
                dog_name = sv.dog.get()
                
                if not dog_name:
                    return
                
                # Get filtered sessions for current dog
                db_ops = DatabaseOperations(self.ui)
                status_filter = sv.session_status_filter.get()
                sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
                
                if not sessions:
                    return
                
                # Extract session numbers from the list of tuples
                session_numbers = [s[0] for s in sessions]
                
                # Find current session in the list
                if current in session_numbers:
                    current_index = session_numbers.index(current)
                    if current_index < len(session_numbers) - 1:  # Can go next
                        next_session = session_numbers[current_index + 1]
                        sv.session_number.set(str(next_session))
                        self.load_session_by_number(next_session)
                        self.update_navigation_buttons()
                
            except ValueError:
                pass
    
    # ========================================
    # SESSION LOADING
    # ========================================
    
    def on_session_number_changed(self, event=None):
        """Called when session number field loses focus or user presses Enter"""
        from sv import sv
        from ui_database import DatabaseOperations
        
        # Clear selected sessions when manually changing session number
        self.ui.selected_sessions = []
        self.ui.selected_sessions_index = -1
        
        try:
            session_num = int(sv.session_number.get())
            if session_num < 1:
                messagebox.showwarning("Invalid Session", "Session number must be at least 1")
                sv.session_number.set("1")
                return
            
            db_ops = DatabaseOperations(self.ui)
            max_session = db_ops.get_next_session_number() - 1  # Current max
            if session_num > max_session + 1:
                messagebox.showwarning(
                    "Session Too High", 
                    f"Session #{session_num} doesn't exist.\n\n"
                    f"Maximum session is #{max_session}.\n"
                    f"Next available is #{max_session + 1}."
                )
                sv.session_number.set(str(max_session + 1))
                return
            
            # Load session data if it exists
            self.load_session_by_number(session_num)
            self.update_navigation_buttons()
            
        except ValueError:
            messagebox.showwarning("Invalid Number", "Session number must be a valid number")
            db_ops = DatabaseOperations(self.ui)
            sv.session_number.set(str(db_ops.get_next_session_number()))
    
    def load_session_by_number(self, session_number):
        """Load session data from database by session number and current dog"""
        from sv import sv
        from ui_database import DatabaseOperations
        from ui_form_management import FormManagement
        import json
        import tkinter as tk
        
        dog_name = sv.dog.get().strip() if sv.dog.get() else ""
        
        # If no dog selected, can't load session
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first")
            return
        
        db_ops = DatabaseOperations(self.ui)
        
        # Get complete session data including related data
        session_dict = db_ops.get_session_with_related_data(session_number, dog_name)
        
        if session_dict:
            # Load basic session data into form fields
            self.ui.set_date(session_dict["date"])
            sv.handler.set(session_dict["handler"])
            sv.session_purpose.set(session_dict["session_purpose"])
            sv.field_support.set(session_dict["field_support"])
            sv.dog.set(session_dict["dog_name"])
            
            # Load search parameters
            sv.location.set(session_dict["location"])
            sv.search_area_size.set(session_dict["search_area_size"])
            sv.num_subjects.set(session_dict["num_subjects"])
            sv.handler_knowledge.set(session_dict["handler_knowledge"])
            sv.weather.set(session_dict["weather"])
            sv.temperature.set(session_dict["temperature"])
            sv.wind_direction.set(session_dict["wind_direction"])
            sv.wind_speed.set(session_dict["wind_speed"])
            sv.search_type.set(session_dict["search_type"])
            sv.drive_level.set(session_dict["drive_level"])
            sv.subjects_found.set(session_dict["subjects_found"])
            
            # Load comments into text widget
            comments = session_dict.get("comments", "")
            self.ui.a_comments_text.delete("1.0", tk.END)
            if comments:
                self.ui.a_comments_text.insert("1.0", comments)
            
            # Load image files
            image_files_str = session_dict.get("image_files", "")
            if image_files_str:
                try:
                    self.ui.map_files_list = json.loads(image_files_str)
                except:
                    self.ui.map_files_list = []
            else:
                self.ui.map_files_list = []
            
            # Update listbox
            self.ui.a_map_listbox.delete(0, tk.END)
            for filename in self.ui.map_files_list:
                self.ui.a_map_listbox.insert(tk.END, filename)
            
            # Update button states
            if self.ui.map_files_list:
                self.ui.a_view_map_button.config(state=tk.NORMAL)
                self.ui.a_delete_map_button.config(state=tk.NORMAL)
            else:
                self.ui.a_view_map_button.config(state=tk.DISABLED)
                self.ui.a_delete_map_button.config(state=tk.DISABLED)
            
            # Load selected terrains
            selected_terrains = session_dict.get("selected_terrains", [])
            self.ui.accumulated_terrains = selected_terrains.copy()
            
            # Update accumulated terrain combo
            if hasattr(self.ui, 'a_accumulated_terrain_combo'):
                self.ui.a_accumulated_terrain_combo['values'] = self.ui.accumulated_terrains
                if self.ui.accumulated_terrains:
                    sv.accumulated_terrain.set(self.ui.accumulated_terrains[0])
                    self.ui.a_accumulated_terrain_combo['state'] = 'readonly'
            
            # Load subject responses into treeview
            subject_responses = session_dict.get("subject_responses", [])
            
            # Clear existing subject responses
            for i in range(1, 11):
                item_id = f'subject_{i}'
                if self.ui.a_subject_responses_tree.exists(item_id):
                    # Disable the item
                    self.ui.a_subject_responses_tree.item(item_id, tags='disabled')
                    # Clear values
                    self.ui.a_subject_responses_tree.item(item_id, values=(
                        f'Subject {i}', '', ''
                    ))
            
            # Populate subject responses
            for response in subject_responses:
                subject_num = response.get("subject_number", 0)
                if 1 <= subject_num <= 10:
                    item_id = f'subject_{subject_num}'
                    if self.ui.a_subject_responses_tree.exists(item_id):
                        # Enable the item
                        self.ui.a_subject_responses_tree.item(item_id, tags='enabled')
                        # Set values
                        self.ui.a_subject_responses_tree.item(item_id, values=(
                            f'Subject {subject_num}',
                            response.get("tfr", ""),
                            response.get("refind", "")
                        ))
            
            # Update subjects found dropdown based on loaded num_subjects
            form_mgmt = FormManagement(self.ui)
            form_mgmt.update_subjects_found()
            
            # Enable delete/undelete buttons (editing existing session)
            self.enable_delete_undelete_buttons()
            
            sv.status.set(f"Loaded session #{session_number}")
            
        else:
            # Session doesn't exist - clear form for new entry
            self.ui.set_date(datetime.now().strftime("%Y-%m-%d"))
            # handler is NOT cleared - keep current handler
            sv.session_purpose.set("")
            sv.field_support.set("")
            # dog is NOT cleared - keep current dog (persists)
            # Clear search parameters
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
            
            # Clear comments
            self.ui.a_comments_text.delete("1.0", tk.END)
            
            # Clear map files list
            self.ui.map_files_list = []
            self.ui.a_map_listbox.delete(0, tk.END)
            self.ui.a_view_map_button.config(state=tk.DISABLED)
            self.ui.a_delete_map_button.config(state=tk.DISABLED)
            
            # Clear selected terrains
            self.ui.accumulated_terrains = []
            if hasattr(self.ui, 'a_accumulated_terrain_combo'):
                self.ui.a_accumulated_terrain_combo['values'] = []
                sv.accumulated_terrain.set("")
            
            # Clear subject responses
            for i in range(1, 11):
                item_id = f'subject_{i}'
                if self.ui.a_subject_responses_tree.exists(item_id):
                    self.ui.a_subject_responses_tree.item(item_id, tags='disabled')
                    self.ui.a_subject_responses_tree.item(item_id, values=(
                        f'Subject {i}', '', ''
                    ))
            
            # Update subjects_found combo state (will disable since num_subjects is blank)
            form_mgmt = FormManagement(self.ui)
            form_mgmt.update_subjects_found()
            
            sv.status.set(f"New session #{session_number}")
    
    def load_prior_session(self):
        """Open dialog to select sessions to view/edit/delete for current dog"""
        from sv import sv
        from ui_database import DatabaseOperations
        
        dog_name = sv.dog.get()
        
        # Check if dog is selected
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first to view their sessions")
            return
        
        db_ops = DatabaseOperations(self.ui)
        status_filter = sv.session_status_filter.get()
        sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter)
        
        if not sessions:
            messagebox.showinfo("No Sessions", f"No training sessions found for {dog_name}.")
            return
        
        # Create selection dialog
        self.show_session_selection_dialog(sessions)
    
    def show_session_selection_dialog(self, sessions):
        """Show dialog for selecting sessions to view/edit"""
        from sv import sv
        
        dialog = tk.Toplevel(self.ui.root)
        dialog.title("Select Sessions to View/Edit/Delete")
        dialog.geometry("600x400")
        dialog.transient(self.ui.root)
        
        # Instructions
        instructions = tk.Label(
            dialog, 
            text="Select sessions to navigate:\n"
                 "• Click to select one session\n"
                 "• Ctrl+Click to select multiple sessions\n"
                 "• Shift+Click to select a range\n"
                 "Use Previous/Next buttons to navigate through selected sessions",
            justify="left",
            padx=10,
            pady=10
        )
        instructions.pack()
        
        # Listbox with scrollbar
        frame = tk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(
            frame, 
            selectmode="extended",  # Allow Ctrl+Click and Shift+Click
            yscrollcommand=scrollbar.set,
            font=("Courier", 10)
        )
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Populate listbox
        for session in sessions:
            session_num, date, handler, dog = session
            handler = handler or ""
            dog = dog or ""
            text = f"Session #{session_num:3d}  |  {date}  |  {handler:20s}  |  {dog}"
            listbox.insert("end", text)
        
        # Store session numbers for reference
        session_numbers = [s[0] for s in sessions]
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_view_selected():
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            # Get selected session numbers
            self.ui.selected_sessions = [session_numbers[i] for i in selected_indices]
            self.ui.selected_sessions_index = 0
            
            # Load the first selected session
            sv.session_number.set(str(self.ui.selected_sessions[0]))
            self.load_session_by_number(self.ui.selected_sessions[0])
            self.update_navigation_buttons()
            
            dialog.destroy()
            sv.status.set(f"Viewing {len(self.ui.selected_sessions)} selected sessions")
        
        def on_delete_selected():
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session to delete")
                return
            
            selected_nums = [session_numbers[i] for i in selected_indices]
            result = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete {len(selected_nums)} session(s)?\n\n"
                f"Sessions: {', '.join(map(str, selected_nums))}\n\n"
                "This action cannot be undone!",
                icon='warning'
            )
            
            if result:
                self.delete_sessions(selected_nums)
                dialog.destroy()
        
        tk.Button(button_frame, text="View Selected", command=on_view_selected,
                 bg="#4169E1", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(button_frame, text="Delete Selected", command=on_delete_selected,
                 bg="#DC143C", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 width=10).pack(side="left", padx=5)
    
    def enable_delete_undelete_buttons(self):
        """Enable the delete/undelete buttons (when editing existing session)"""
        if hasattr(self.ui, 'a_delete_undelete_frame'):
            for child in self.ui.a_delete_undelete_frame.winfo_children():
                child.config(state="normal")
    
    def disable_delete_undelete_buttons(self):
        """Disable the delete/undelete buttons (when creating new session)"""
        if hasattr(self.ui, 'a_delete_undelete_frame'):
            for child in self.ui.a_delete_undelete_frame.winfo_children():
                child.config(state="disabled")
    
    def delete_current_session(self):
        """Mark the current session as deleted"""
        from sv import sv
        from ui_database import DatabaseOperations
        from tkinter import messagebox
        
        session_number = sv.session_number.get()
        dog_name = sv.dog.get()
        
        if not dog_name or not session_number:
            return
        
        try:
            session_num = int(session_number)
        except ValueError:
            return
        
        # Confirm
        result = messagebox.askyesno(
            "Mark as Deleted",
            f"Mark session #{session_num} for {dog_name} as deleted?\n\n"
            "This can be undone with the Undelete button.",
            icon='warning'
        )
        
        if result:
            db_ops = DatabaseOperations(self.ui)
            success = db_ops.update_session_status(session_num, dog_name, 'deleted')
            
            if success:
                sv.status.set(f"Session #{session_num} marked as deleted")
                messagebox.showinfo("Success", f"Session #{session_num} marked as deleted")
                
                # Refresh navigation to reflect filter
                self.update_navigation_buttons()
            else:
                messagebox.showerror("Error", "Failed to mark session as deleted")
    
    def undelete_current_session(self):
        """Mark the current session as active (undelete)"""
        from sv import sv
        from ui_database import DatabaseOperations
        from tkinter import messagebox
        
        session_number = sv.session_number.get()
        dog_name = sv.dog.get()
        
        if not dog_name or not session_number:
            return
        
        try:
            session_num = int(session_number)
        except ValueError:
            return
        
        # Confirm
        result = messagebox.askyesno(
            "Undelete Session",
            f"Mark session #{session_num} for {dog_name} as active?",
            icon='question'
        )
        
        if result:
            db_ops = DatabaseOperations(self.ui)
            success = db_ops.update_session_status(session_num, dog_name, 'active')
            
            if success:
                sv.status.set(f"Session #{session_num} restored to active")
                messagebox.showinfo("Success", f"Session #{session_num} restored to active")
                
                # Refresh navigation to reflect filter
                self.update_navigation_buttons()
            else:
                messagebox.showerror("Error", "Failed to restore session")
    
    def delete_current_session(self):
        """Mark the current session as deleted"""
        from sv import sv
        from ui_database import DatabaseOperations
        from tkinter import messagebox
        
        session_number = sv.session_number.get()
        dog_name = sv.dog.get()
        
        if not dog_name or not session_number:
            return
        
        try:
            session_num = int(session_number)
        except ValueError:
            return
        
        # Get the actual database session number (not the displayed computed number)
        # We need to find which database session is currently loaded
        # For now, we'll need to store the database session_number when loading
        # This is a limitation we'll address by storing it in a variable
        
        # Confirm
        result = messagebox.askyesno(
            "Mark as Deleted",
            f"Mark this session for {dog_name} as deleted?\n\n"
            "This can be undone with the Undelete button.",
            icon='warning'
        )
        
        if result:
            db_ops = DatabaseOperations(self.ui)
            # Use the database session number stored when session was loaded
            if hasattr(self, 'current_db_session_number'):
                success = db_ops.update_session_status(self.current_db_session_number, dog_name, 'deleted')
                
                if success:
                    sv.status.set(f"Session marked as deleted")
                    messagebox.showinfo("Success", "Session marked as deleted")
                    
                    # Reload session to update display
                    self.load_session_by_number(self.current_db_session_number)
                else:
                    messagebox.showerror("Error", "Failed to mark session as deleted")
    
    def undelete_current_session(self):
        """Mark the current session as active (undelete)"""
        from sv import sv
        from ui_database import DatabaseOperations
        from tkinter import messagebox
        
        session_number = sv.session_number.get()
        dog_name = sv.dog.get()
        
        if not dog_name or not session_number:
            return
        
        try:
            session_num = int(session_number)
        except ValueError:
            return
        
        # Confirm
        result = messagebox.askyesno(
            "Undelete Session",
            f"Mark this session for {dog_name} as active?",
            icon='question'
        )
        
        if result:
            db_ops = DatabaseOperations(self.ui)
            # Use the database session number stored when session was loaded
            if hasattr(self, 'current_db_session_number'):
                success = db_ops.update_session_status(self.current_db_session_number, dog_name, 'active')
                
                if success:
                    sv.status.set(f"Session restored to active")
                    messagebox.showinfo("Success", "Session restored to active")
                    
                    # Reload session to update display
                    self.load_session_by_number(self.current_db_session_number)
                else:
                    messagebox.showerror("Error", "Failed to restore session")
    
        def on_status_filter_changed(self):
        """Handle status filter radio button change - update status bar"""
        from sv import sv
        
        # Get current filter
        status_filter = sv.session_status_filter.get()
        
        # Update status bar
        filter_label = {"active": "Active", "deleted": "Deleted", "both": "All"}[status_filter]
        dog_name = sv.dog.get()
        if dog_name:
            sv.status.set(f"Filter: {filter_label} sessions for {dog_name}")
        else:
            sv.status.set(f"Filter: {filter_label}")
    
    def delete_sessions(self, session_numbers):
        """Delete multiple sessions from database for current dog"""
        from sv import sv
        from ui_database import DatabaseOperations
        from ui_form_management import FormManagement
        
        dog_name = sv.dog.get()
        
        db_ops = DatabaseOperations(self.ui)
        success = db_ops.delete_sessions(session_numbers, dog_name)
        
        if success:
            messagebox.showinfo("Success", f"Deleted {len(session_numbers)} session(s)")
            
            # Clear selected sessions and reset to new session
            self.ui.selected_sessions = []
            self.ui.selected_sessions_index = -1
            
            form_mgmt = FormManagement(self.ui)
            form_mgmt.new_session()
