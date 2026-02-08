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
Trailing Helper Module
Contains helper methods for the Trailing Training Session tab.
These methods handle data manipulation, callbacks, and business logic.
"""
import tkinter as tk
from tkinter import messagebox, Toplevel, Listbox, Scrollbar
from datetime import datetime
import re
import sv
from ui_utils import get_username, save_json_mirrored


class TrailingHelper:
    """
    Mixin class containing helper methods for Trailing tab.
    These methods should be mixed into the main TrainingLoggerUI class.
    """
    
    # =========================================================================
    # SESSION SAVE
    # =========================================================================
    
    def on_trailing_session_save(self, session_data):
        """Handle trailing session save from entry tab"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        db_ops = TDatabaseOperations(self)
        
        is_update = hasattr(self.trailing_entry, 'editing_session') and self.trailing_entry.editing_session
        
        success, session_id, message = db_ops.save_session(session_data, is_update)
        
        if success:
            if session_id:
                # Save terrains from listbox
                terrains = list(self.trailing_entry.terrain_listbox.get(0, tk.END))
                db_ops.save_selected_terrains(session_id, terrains)
                
                # Save purposes from listbox
                purposes = list(self.trailing_entry.purpose_listbox.get(0, tk.END))
                db_ops.save_selected_purposes(session_id, purposes)
                
                # Save distractions from treeview
                distractions = []
                for item in self.trailing_entry.distraction_tree.get_children():
                    values = self.trailing_entry.distraction_tree.item(item, 'values')
                    if len(values) >= 2:
                        distractions.append({
                            "type": values[0],
                            "response": values[1]
                        })
                db_ops.save_distractions(session_id, distractions)
                
                # Save to JSON backup
                # self._save_trailing_session_to_json(session_data, terrains, purposes, distractions)
            
            # Clear form and prepare for next session
            self.trailing_entry.clear_form()
            
            # Save last handler and dog to config
            current_handler = sv.t_handler.get()
            current_dog = sv.t_dog.get()
            if "trailing" not in self.config:
                self.config["trailing"] = {}
            if current_handler:
                self.config["trailing"]["default_handler"] = current_handler
            if current_dog:
                self.config["trailing"]["last_dog"] = current_dog
            self.save_config()
            
            self.show_status_message(message, "info")
            return True
        else:
            # print(f"ERROR saving trailing session: {message}")
            self.show_status_message(f"Error: {message}", "error")
            return False
    
    # def _save_trailing_session_to_json(self, session_data, terrains, purposes, distractions):
    #     """Save trailing session to JSON backup file."""
    #     try:
    #         user_name = get_username()
            
    #         backup_data = {
    #             **session_data,
    #             "selected_terrains": terrains,
    #             "selected_purposes": purposes,
    #             "distractions": distractions,
    #             "user_name": user_name,
    #             "update_time": datetime.now().isoformat()
    #         }
            
    #         dog_name = session_data.get('t_dog_name', 'unknown')
    #         session_num = session_data.get('t_session_number', '0')
            
    #         safe_user_name = re.sub(r'[^\w\-]', '_', user_name) if user_name else 'unknown'
    #         safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
            
    #         filename = f"t_{safe_user_name}_{safe_dog_name}_{session_num}.json"
            
    #         primary, secondary, checksum, primary_ts, secondary_ts = save_json_mirrored(filename, backup_data)
            
    #         # if primary:
    #         #     print(f"Trailing session saved to JSON: {primary}")
    #         # if secondary:
    #         #     print(f"Trailing session mirrored to: {secondary}")
                
    #     except Exception as e:
    #         # print(f"Warning: Failed to save trailing session to JSON: {e}")
    #         self.show_status_message(f"Backup failed: {str(e)}", "error")
    
    # =========================================================================
    # SESSION NUMBER
    # =========================================================================
    
    def get_trailing_next_session_number(self, dog_name):
        """Get next session number for a dog in trailing"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        db_ops = TDatabaseOperations(self)
        return db_ops.get_next_session_number(dog_name)
    
    # =========================================================================
    # LOAD PRIOR SESSION DIALOG
    # =========================================================================
    
    def on_trailing_load_prior_session(self):
        """Open dialog to view/edit/hide prior trailing sessions"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        if sv.sync_in_progress:
            messagebox.showinfo("Sync In Progress",
                "Please wait - background sync is in progress.")
            return
        
        dog_name = sv.t_dog.get()
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first.")
            return
        
        db_ops = TDatabaseOperations(self)
        status_filter = sv.t_session_status_filter.get()
        sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter=status_filter.capitalize())
        
        if not sessions:
            messagebox.showinfo("No Sessions", f"No trailing sessions found for {dog_name}")
            return
        
        # Create selection dialog
        dialog = Toplevel(self.root)
        dialog.title("Select Trailing Sessions to View/Edit/Hide")
        dialog.geometry("650x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        instructions = tk.Label(dialog,
            text="Select sessions to navigate:\n"
                 "\N{Bullet} Click to select one session\n"
                 "\N{Bullet} Ctrl+Click to select multiple sessions\n"
                 "\N{Bullet} Shift+Click to select a range",
            justify="left", padx=10, pady=10)
        instructions.pack()
        
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        session_listbox = Listbox(list_frame, selectmode="extended", yscrollcommand=scrollbar.set,
                                  font=("Courier", 10), width=70)
        session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=session_listbox.yview)
        
        session_data_list = []
        
        def populate_listbox(sessions_to_show):
            session_listbox.delete(0, tk.END)
            session_data_list.clear()
            
            for session in sessions_to_show:
                session_num = session.get('t_session_number', '?')
                date = session.get('t_date', '')
                handler = session.get('t_handler', '') or ''
                location = session.get('t_location', '') or ''
                status = session.get('status', 'active')
                status_marker = " [HIDDEN]" if status == 'deleted' else ""
                
                display_text = f"#{session_num:3d}  |  {str(date):10s}  |  {handler:15s}  |  {location:20s}{status_marker}"
                session_listbox.insert(tk.END, display_text)
                session_data_list.append(session)
        
        populate_listbox(sessions)
        self.trailing_entry.dog_sessions_list = sessions
        
        def refresh_sessions():
            status_filter = sv.t_session_status_filter.get()
            new_sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter=status_filter.capitalize())
            populate_listbox(new_sessions)
            self.trailing_entry.dog_sessions_list = new_sessions
            
            if status_filter == 'deleted':
                delete_button.config(text="Restore Selected", bg="#28a745")
            else:
                delete_button.config(text="Hide Selected", bg="#DC143C")
        
        filter_frame = tk.Frame(dialog)
        filter_frame.pack(pady=(5, 0))
        
        tk.Label(filter_frame, text="Show Sessions:").pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(filter_frame, text="Active", variable=sv.t_session_status_filter,
                      value="active", command=refresh_sessions).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(filter_frame, text="Hidden", variable=sv.t_session_status_filter,
                      value="deleted", command=refresh_sessions).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(filter_frame, text="Both", variable=sv.t_session_status_filter,
                      value="all", command=refresh_sessions).pack(side=tk.LEFT, padx=5)
        
        def view_selected():
            selected_indices = session_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            selected_sessions = [session_data_list[i] for i in selected_indices]
            self.trailing_entry.dog_sessions_list = selected_sessions
            self.trailing_entry.current_session_index = 0
            
            self._load_trailing_session_into_form(selected_sessions[0])
            self._update_trailing_navigation_buttons()
            
            # Reset filter to active for next dialog open
            sv.t_session_status_filter.set("active")
            dialog.destroy()
            self.show_status_message(f"Viewing {len(selected_sessions)} selected trailing session(s)", "info")
        
        def delete_restore_selected():
            selected_indices = session_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session")
                return
            
            selected_sessions = [session_data_list[i] for i in selected_indices]
            selected_nums = [s.get('t_session_number') for s in selected_sessions]
            status_filter = sv.t_session_status_filter.get()
            
            if status_filter == 'deleted':
                result = messagebox.askyesno("Confirm Restore",
                    f"Restore {len(selected_nums)} session(s) to active?\n\nSessions: {', '.join(map(str, selected_nums))}",
                    icon='question')
                if result:
                    for session_num in selected_nums:
                        db_ops.update_session_status(session_num, dog_name, 'active')
                    self.show_status_message(f"Restored {len(selected_nums)} trailing session(s)", "info")
                    # Reset filter to active for next dialog open
                    sv.t_session_status_filter.set("active")
                    # Clear session list and reset form for new entry
                    self.trailing_entry.dog_sessions_list = []
                    self.trailing_entry.current_session_index = -1
                    self.trailing_entry.editing_session = False
                    self.trailing_entry.editing_row = None
                    # Update session number to next available
                    next_session = self.get_trailing_next_session_number(dog_name)
                    sv.t_session.set(str(next_session))
                    self.trailing_entry.update_session_frame_title('active')
                    dialog.destroy()
            else:
                result = messagebox.askyesno("Confirm Hide",
                    f"Mark {len(selected_nums)} session(s) as hidden?\n\nSessions: {', '.join(map(str, selected_nums))}",
                    icon='warning')
                if result:
                    for session_num in selected_nums:
                        db_ops.update_session_status(session_num, dog_name, 'deleted')
                    self.show_status_message(f"Hidden {len(selected_nums)} trailing session(s)", "info")
                    # Reset filter to active for next dialog open
                    sv.t_session_status_filter.set("active")
                    # Clear session list and reset form for new entry
                    self.trailing_entry.dog_sessions_list = []
                    self.trailing_entry.current_session_index = -1
                    self.trailing_entry.editing_session = False
                    self.trailing_entry.editing_row = None
                    # Update session number to next available
                    next_session = self.get_trailing_next_session_number(dog_name)
                    sv.t_session.set(str(next_session))
                    self.trailing_entry.update_session_frame_title('active')
                    dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="View Selected", command=view_selected,
                  bg="#4169E1", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        
        status_filter = sv.t_session_status_filter.get()
        button_text = "Restore Selected" if status_filter == 'deleted' else "Hide Selected"
        button_color = "#28a745" if status_filter == 'deleted' else "#DC143C"
        
        delete_button = tk.Button(btn_frame, text=button_text, command=delete_restore_selected,
                                   bg=button_color, fg="white", width=15)
        delete_button.pack(side=tk.LEFT, padx=5)
        
        def on_cancel():
            # Reset filter to active for next dialog open
            sv.t_session_status_filter.set("active")
            dialog.destroy()
        
        tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
        
        # Also reset filter if dialog is closed via window manager (X button)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        
        session_listbox.bind('<Double-Button-1>', lambda e: view_selected())
    
    # =========================================================================
    # LOAD SESSION INTO FORM
    # =========================================================================
    
    def _load_trailing_session_into_form(self, session_data):
        """Load trailing session data into the form for editing"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        self.trailing_entry.set_session_data(session_data)
        self.trailing_entry.editing_session = True
        self.trailing_entry.editing_row = session_data.get('id')
        self.trailing_entry.update_save_button_text()
        
        session_id = session_data.get('id')
        if session_id:
            db_ops = TDatabaseOperations(self)
            
            terrains = db_ops.load_selected_terrains(session_id)
            self.trailing_entry.set_selected_terrains(terrains)
            
            purposes = db_ops.load_selected_purposes(session_id)
            self.trailing_entry.set_selected_purposes(purposes)
            
            distractions = db_ops.load_distractions(session_id)
            self.trailing_entry.set_distractions(distractions)
        
        session_status = session_data.get('status', 'active')
        if session_status == 'deleted':
            if hasattr(self.trailing_entry, 'hide_btn'):
                self.trailing_entry.hide_btn.config(state=tk.DISABLED)
            if hasattr(self.trailing_entry, 'resume_btn'):
                self.trailing_entry.resume_btn.config(state=tk.NORMAL)
        else:
            if hasattr(self.trailing_entry, 'hide_btn'):
                self.trailing_entry.hide_btn.config(state=tk.NORMAL)
            if hasattr(self.trailing_entry, 'resume_btn'):
                self.trailing_entry.resume_btn.config(state=tk.DISABLED)
        
        self.show_status_message(f"Loaded trailing session {session_data.get('t_session_number')} for editing", "info")
    
    # =========================================================================
    # NAVIGATION
    # =========================================================================
    
    def _update_trailing_navigation_buttons(self):
        """Update prev/next button states for trailing"""
        if not self.trailing_entry.dog_sessions_list:
            self.trailing_entry.prev_session_btn.config(state=tk.DISABLED)
            self.trailing_entry.next_session_btn.config(state=tk.DISABLED)
            return
        
        idx = self.trailing_entry.current_session_index
        max_idx = len(self.trailing_entry.dog_sessions_list) - 1
        
        self.trailing_entry.prev_session_btn.config(state=tk.NORMAL if idx > 0 else tk.DISABLED)
        self.trailing_entry.next_session_btn.config(state=tk.NORMAL if idx < max_idx else tk.DISABLED)
    
    def on_trailing_navigate_previous(self):
        """Navigate to previous trailing session"""
        if not self.trailing_entry.dog_sessions_list:
            return
        
        idx = self.trailing_entry.current_session_index
        if idx > 0:
            self.trailing_entry.current_session_index = idx - 1
            session = self.trailing_entry.dog_sessions_list[idx - 1]
            self._load_trailing_session_into_form(session)
            self._update_trailing_navigation_buttons()
    
    def on_trailing_navigate_next(self):
        """Navigate to next trailing session"""
        if not self.trailing_entry.dog_sessions_list:
            return
        
        idx = self.trailing_entry.current_session_index
        max_idx = len(self.trailing_entry.dog_sessions_list) - 1
        if idx < max_idx:
            self.trailing_entry.current_session_index = idx + 1
            session = self.trailing_entry.dog_sessions_list[idx + 1]
            self._load_trailing_session_into_form(session)
            self._update_trailing_navigation_buttons()
    
    # =========================================================================
    # RESUME / HIDE SESSION
    # =========================================================================
    
    def on_trailing_resume_session(self):
        """Restore the currently displayed trailing session"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        if not self.trailing_entry.editing_session:
            return
        
        dog_name = sv.t_dog.get()
        session_number = sv.t_session.get()
        
        if not dog_name or not session_number:
            return
        
        try:
            session_num = int(session_number)
        except ValueError:
            return
        
        result = messagebox.askyesno("Restore Session",
            f"Mark trailing session {session_num} for {dog_name} as active?",
            icon='question')
        
        if result:
            db_ops = TDatabaseOperations(self)
            success = db_ops.update_session_status(session_num, dog_name, 'active')
            
            if success:
                self.show_status_message(f"Trailing session {session_num} restored to active", "info")
                
                for session in self.trailing_entry.dog_sessions_list:
                    if session.get('t_session_number') == session_num:
                        session['status'] = 'active'
                        break
                
                idx = self.trailing_entry.current_session_index
                if 0 <= idx < len(self.trailing_entry.dog_sessions_list):
                    self._load_trailing_session_into_form(self.trailing_entry.dog_sessions_list[idx])
            else:
                messagebox.showerror("Error", "Failed to restore trailing session")
    
    def on_trailing_hide_session(self):
        """Mark the currently displayed trailing session as hidden"""
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        if not self.trailing_entry.editing_session:
            return
        
        dog_name = sv.t_dog.get()
        session_number = sv.t_session.get()
        
        if not dog_name or not session_number:
            return
        
        try:
            session_num = int(session_number)
        except ValueError:
            return
        
        result = messagebox.askyesno("Hide Session",
            f"Mark trailing session {session_num} for {dog_name} as hidden?\n\nThis can be undone with the Restore button.",
            icon='warning')
        
        if result:
            db_ops = TDatabaseOperations(self)
            success = db_ops.update_session_status(session_num, dog_name, 'deleted')
            
            if success:
                self.show_status_message(f"Trailing session {session_num} marked as hidden", "info")
                
                for session in self.trailing_entry.dog_sessions_list:
                    if session.get('t_session_number') == session_num:
                        session['status'] = 'deleted'
                        break
                
                idx = self.trailing_entry.current_session_index
                if 0 <= idx < len(self.trailing_entry.dog_sessions_list):
                    self._load_trailing_session_into_form(self.trailing_entry.dog_sessions_list[idx])
            else:
                messagebox.showerror("Error", "Failed to hide trailing session")
    
    # =========================================================================
    # EXPORT PDF
    # =========================================================================
    
    def on_trailing_export_pdf(self):
        """Export trailing sessions to PDF using list-based selection"""
        from tkinter import Toplevel, Listbox, Scrollbar, filedialog
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        dog_name = sv.t_dog.get()
        if not dog_name:
            messagebox.showwarning("No Dog Selected", "Please select a dog first.")
            return
        
        # Create dialog
        dialog = Toplevel(self.root)
        dialog.title("Export Trailing Sessions to PDF")
        dialog.geometry("650x500")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog over main window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Dog display at top
        header_frame = tk.Frame(dialog, padx=10, pady=10)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="Dog:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(header_frame, text=dog_name, font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(5, 0))
        
        # Instructions
        instructions = tk.Label(
            dialog,
            text="Select sessions to export:\n"
                 "\N{Bullet} Click to select one session\n"
                 "\N{Bullet} Ctrl+Click to select multiple sessions\n"
                 "\N{Bullet} Shift+Click to select a range",
            justify="left",
            padx=10,
            pady=5
        )
        instructions.pack()
        
        # Status filter radiobuttons
        filter_frame = tk.Frame(dialog)
        filter_frame.pack(pady=(5, 5))
        
        tk.Label(filter_frame, text="Show Sessions:").pack(side=tk.LEFT, padx=(0, 10))
        export_status_var = tk.StringVar(value="active")
        
        # Listbox with scrollbar
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        session_listbox = Listbox(list_frame, selectmode="extended", yscrollcommand=scrollbar.set,
                                  font=("Courier", 10), width=70)
        session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=session_listbox.yview)
        
        # Store session data for lookup
        session_data_list = []
        
        def populate_listbox():
            """Populate the listbox with session data"""
            session_listbox.delete(0, tk.END)
            session_data_list.clear()
            
            db_ops = TDatabaseOperations(self)
            status_filter = export_status_var.get()
            sessions = db_ops.get_all_sessions_for_dog(dog_name, status_filter=status_filter.capitalize() if status_filter != "both" else "All")
            
            for session in sessions:
                session_num = session.get('t_session_number', '?')
                date = session.get('t_date', '')
                handler = session.get('t_handler', '') or ''
                location = session.get('t_location', '') or ''
                status = session.get('status', 'active')
                status_marker = " [HIDDEN]" if status == 'deleted' else ""
                
                display_text = f"#{session_num:3d}  |  {str(date):10s}  |  {handler:15s}  |  {location:20s}{status_marker}"
                session_listbox.insert(tk.END, display_text)
                session_data_list.append(session)
            
            # Select all by default
            if session_data_list:
                session_listbox.select_set(0, tk.END)
        
        def on_filter_changed():
            """Handle filter radiobutton change"""
            populate_listbox()
        
        # Add radiobuttons
        tk.Radiobutton(filter_frame, text="Active", variable=export_status_var,
                      value="active", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(filter_frame, text="Hidden", variable=export_status_var,
                      value="deleted", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(filter_frame, text="Both", variable=export_status_var,
                      value="both", command=on_filter_changed).pack(side=tk.LEFT, padx=5)
        
        # Initial population
        populate_listbox()
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def do_export():
            selected_indices = session_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one session to export")
                return
            
            # Get selected sessions
            selected_sessions = [session_data_list[i] for i in selected_indices]
            selected_nums = [s.get('t_session_number') for s in selected_sessions]
            
            # Get pdf_folder from sv
            import os
            pdf_folder = sv.pdf_folder.get().strip()
            
            # Build filepath using pdf_folder if set, otherwise ask user
            default_filename = f"Trailing_Log_{dog_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            if pdf_folder and os.path.isdir(pdf_folder):
                # Use the configured PDF folder
                filepath = os.path.join(pdf_folder, default_filename)
                # Check if file exists and ask to overwrite
                if os.path.exists(filepath):
                    if not messagebox.askyesno("File Exists", 
                        f"File already exists:\n{filepath}\n\nOverwrite?"):
                        return
            else:
                # No PDF folder configured, ask user for location
                filepath = filedialog.asksaveasfilename(
                    parent=dialog,
                    title="Save PDF As",
                    defaultextension=".pdf",
                    initialfile=default_filename,
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
                )
                
                if not filepath:
                    return
            
            dialog.destroy()
            
            # Export with selected sessions
            self._export_trailing_sessions_by_selection(filepath, dog_name, selected_nums)
        
        tk.Button(button_frame, text="Export", command=do_export, bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
    
    def _export_trailing_sessions_by_selection(self, filepath, dog_name, session_numbers):
        """Export selected trailing sessions to PDF"""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_CENTER
        from t_ui_database import DatabaseOperations as TDatabaseOperations
        
        try:
            # Fetch sessions using get_trailing_sessions_by_numbers
            db_ops = TDatabaseOperations(self)
            sessions = db_ops.get_trailing_sessions_by_numbers(dog_name, session_numbers)
            
            if not sessions:
                messagebox.showinfo("No Sessions", "No sessions found to export")
                return
            
            # Load related data for each session
            for session_data in sessions:
                session_id = session_data.get('id')
                if session_id:
                    session_data['terrains'] = db_ops.load_selected_terrains(session_id)
                    session_data['purposes'] = db_ops.load_selected_purposes(session_id)
                    session_data['distractions'] = db_ops.load_distractions(session_id)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                    rightMargin=0.5*inch, leftMargin=0.5*inch,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#2E4057'),
                spaceAfter=20,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#4CAF50'),
                spaceAfter=6,
                spaceBefore=6
            )
            
            label_style = ParagraphStyle(
                'Label',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                spaceAfter=2
            )
            
            value_style = ParagraphStyle(
                'Value',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=8
            )
            
            elements = []
            
            # Title
            elements.append(Paragraph(f"Trailing Training Log for {dog_name}", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            def add_field(label, value):
                if value and str(value).strip():
                    return [Paragraph(f"<b>{label}:</b>", label_style),
                            Paragraph(str(value), value_style)]
                return None
            
            def format_time_for_pdf(time_value):
                """Format time value with ' hours' suffix for clarity in PDF"""
                if time_value and str(time_value).strip():
                    return f"{time_value} hours"
                return None
            
            for i, session_data in enumerate(sessions):
                if i > 0:
                    if i % 2 == 0:
                        elements.append(PageBreak())
                    else:
                        elements.append(Spacer(1, 0.15*inch))
                        elements.append(Table([['']], colWidths=[7*inch],
                                         style=[('LINEABOVE', (0,0), (-1,-1), 1, colors.grey)]))
                        elements.append(Spacer(1, 0.15*inch))
                
                # Session header
                session_num = session_data.get('t_session_number', '?')
                date_str = str(session_data.get('t_date', '')) if session_data.get('t_date') else ''
                elements.append(Paragraph(f"<b>Session #{session_num}</b> - {date_str}", heading_style))
                elements.append(Spacer(1, 0.1*inch))
                
                # Session Information
                elements.append(Paragraph("<b>Session Information</b>", heading_style))
                session_info_data = []
                
                # Format time values
                start_time_val = session_data.get('t_start_time')
                finish_time_val = session_data.get('t_finish_time')
                start_time_formatted = f"{start_time_val} hours" if start_time_val and str(start_time_val).strip() else None
                finish_time_formatted = f"{finish_time_val} hours" if finish_time_val and str(finish_time_val).strip() else None
                
                fields = [
                    ('Handler', session_data.get('t_handler')),
                    ('Field Support', session_data.get('t_field_support')),
                    ('Location', session_data.get('t_location')),
                    ('Start Time', start_time_formatted),
                    ('Finish Time', finish_time_formatted),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        session_info_data.append(row)
                
                purposes = session_data.get('purposes', [])
                if purposes:
                    purposes_str = ', '.join(purposes) if isinstance(purposes, list) else str(purposes)
                    row = add_field('Session Purposes', purposes_str)
                    if row:
                        session_info_data.append(row)
                
                if session_info_data:
                    table = Table(session_info_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                elements.append(Spacer(1, 0.1*inch))
                
                # Trail Details
                elements.append(Paragraph("<b>Trail Details</b>", heading_style))
                trail_info_data = []
                
                fields = [
                    ('Trail Age', session_data.get('t_trail_age')),
                    ('Trail Length', session_data.get('t_trail_length')),
                    ('Difficulty', session_data.get('t_difficulty')),
                    ('Trail Layer', session_data.get('t_trail_layer')),
                    ('Cross-Track Layer', session_data.get('t_cross_track_layer')),
                    ('Cross-Track Age', session_data.get('t_cross_track_age')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        trail_info_data.append(row)
                
                terrains = session_data.get('terrains', [])
                if terrains:
                    terrain_text = ", ".join(terrains)
                    row = add_field('Terrain Types', terrain_text)
                    if row:
                        trail_info_data.append(row)
                
                if trail_info_data:
                    table = Table(trail_info_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                elements.append(Spacer(1, 0.1*inch))
                
                # Weather - Laying
                weather_laying_data = []
                fields = [
                    ('Weather (Laying)', session_data.get('t_weather_laying')),
                    ('Temperature (Laying)', session_data.get('t_temp_laying')),
                    ('Wind Speed (Laying)', session_data.get('t_wind_laying')),
                    ('Wind Direction (Laying)', session_data.get('t_wind_direction_laying')),
                    ('Humidity (Laying)', session_data.get('t_humidity_laying')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        weather_laying_data.append(row)
                
                # Weather - Running
                weather_running_data = []
                fields = [
                    ('Weather (Running)', session_data.get('t_weather_running')),
                    ('Temperature (Running)', session_data.get('t_temp_running')),
                    ('Wind Speed (Running)', session_data.get('t_wind_running')),
                    ('Wind Direction (Running)', session_data.get('t_wind_direction_running')),
                    ('Humidity (Running)', session_data.get('t_humidity_running')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        weather_running_data.append(row)
                
                # Add weather section if we have any weather data
                if weather_laying_data or weather_running_data:
                    elements.append(Paragraph("<b>Weather Conditions</b>", heading_style))
                    all_weather_data = weather_laying_data + weather_running_data
                    table = Table(all_weather_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 0.1*inch))
                
                # Dog Behavior
                elements.append(Paragraph("<b>Dog Behavior</b>", heading_style))
                behavior_data = []
                
                fields = [
                    ('Start Behavior', session_data.get('t_start_behavior')),
                    ('Consistency', session_data.get('t_consistency')),
                    ('Head Position', session_data.get('t_head_pos')),
                    ('Pace', session_data.get('t_pace')),
                    ('Indication', session_data.get('t_indication')),
                    ('Time to Complete', session_data.get('t_time')),
                    ('Success Rate', session_data.get('t_success')),
                ]
                for label, value in fields:
                    row = add_field(label, value)
                    if row:
                        behavior_data.append(row)
                
                if behavior_data:
                    table = Table(behavior_data, colWidths=[1.5*inch, 5.5*inch])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,-1), 2),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ]))
                    elements.append(table)
                elements.append(Spacer(1, 0.1*inch))
                
                # Distractions
                distractions = session_data.get('distractions', [])
                if distractions:
                    elements.append(Paragraph("<b>Distractions</b>", heading_style))
                    distraction_data = [['Type', 'Response']]
                    for d in distractions:
                        distraction_data.append([d.get('type', ''), d.get('response', '')])
                    
                    table = Table(distraction_data, colWidths=[2*inch, 5*inch])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F5')),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 0.1*inch))
                
                # Maps, Images, and Videos
                map_files_str = session_data.get('t_map_files', '')
                trail_maps_folder = sv.trail_maps_folder.get().strip()
                
                if map_files_str and trail_maps_folder:
                    import json
                    import shutil
                    import os
                    
                    # Parse image files - stored as JSON list
                    image_files = []
                    if map_files_str:
                        try:
                            parsed = json.loads(map_files_str)
                            if isinstance(parsed, list):
                                image_files = [f.strip() for f in parsed if f and f.strip()]
                            else:
                                image_files = [str(parsed).strip()] if parsed else []
                        except (json.JSONDecodeError, TypeError):
                            image_files = [f.strip() for f in map_files_str.replace(';', ',').split(',') if f.strip()]
                    
                    if image_files:
                        from reportlab.platypus import Image
                        elements.append(Paragraph("<b>Maps, Images, and Videos</b>", heading_style))
                        
                        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
                        pdf_folder = os.path.dirname(filepath)
                        
                        for image_file in image_files:
                            if image_file:
                                if os.path.isabs(image_file):
                                    image_path = image_file
                                else:
                                    image_path = os.path.join(trail_maps_folder, image_file)
                                
                                display_name = os.path.basename(image_file)
                                
                                if os.path.exists(image_path):
                                    try:
                                        file_ext = os.path.splitext(image_file)[1].lower()
                                        
                                        if file_ext in ['.jpg', '.jpeg', '.png']:
                                            # Embed image in PDF
                                            img = Image(image_path, width=6.5*inch, height=6.5*inch, kind='proportional')
                                            elements.append(img)
                                            elements.append(Spacer(1, 0.05*inch))
                                            caption = Paragraph(f"<i>{display_name}</i>", label_style)
                                            elements.append(caption)
                                            elements.append(Spacer(1, 0.1*inch))
                                        elif file_ext == '.pdf':
                                            note_text = f"<i>{display_name}</i><br/><font color='blue'>PDF file (not embedded)</font>"
                                            elements.append(Paragraph(note_text, value_style))
                                            elements.append(Spacer(1, 0.1*inch))
                                        elif file_ext in video_extensions:
                                            # Copy video to PDF output folder and create link
                                            video_dest = os.path.join(pdf_folder, display_name)
                                            
                                            if not os.path.exists(video_dest):
                                                try:
                                                    shutil.copy2(image_path, video_dest)
                                                    # print(f"[PDF Export] Copied video to: {video_dest}")
                                                    pass
                                                except Exception as copy_err:
                                                    # print(f"[PDF Export] Warning: Could not copy video: {copy_err}")
                                                    pass
                                            
                                            # Use file:/// URI for reliable opening in PDF viewers
                                            video_uri = 'file:///' + video_dest.replace('\\', '/').replace(' ', '%20')
                                            video_link = f'<a href="{video_uri}" color="blue"><u>{display_name}</u></a>'
                                            note_text = f"<b>Video:</b> {video_link}<br/><font color='gray' size='8'>(Video file copied to PDF folder - click to open)</font>"
                                            elements.append(Paragraph(note_text, value_style))
                                            elements.append(Spacer(1, 0.1*inch))
                                    except Exception as e:
                                        error_text = f"<i>{display_name}</i><br/><font color='red'>Error loading file: {str(e)}</font>"
                                        elements.append(Paragraph(error_text, value_style))
                                        elements.append(Spacer(1, 0.1*inch))
                                else:
                                    error_text = f"<i>{display_name}</i><br/><font color='red'>File not found</font>"
                                    elements.append(Paragraph(error_text, value_style))
                                    elements.append(Spacer(1, 0.1*inch))
                
                # Notes/Impression
                notes = session_data.get('t_impression')
                if notes and str(notes).strip():
                    elements.append(Paragraph("<b>Notes</b>", heading_style))
                    elements.append(Paragraph(str(notes), value_style))
            
            # Build PDF
            doc.build(elements)
            
            self.show_status_message(f"PDF exported: {filepath}", "info")
            
            # Ask to open the PDF
            if messagebox.askyesno("Open File?", "Would you like to open the exported PDF?"):
                import subprocess
                import platform
                import os
                if platform.system() == 'Windows':
                    os.startfile(filepath)
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', filepath])
                else:
                    subprocess.run(['xdg-open', filepath])
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Export Error", f"Failed to export PDF:\n{str(e)}")
    
    # =========================================================================
    # INITIAL DATA LOADING
    # =========================================================================
    
    def load_trailing_initial_data(self):
        """Load initial data for the trailing tab"""
        from ui_database import get_db_manager
        from ui_utils import get_default_terrain_types, get_default_distraction_types
        
        try:
            # Load dog names
            dog_names = self._get_dog_names()
            # print(f"DEBUG: Trailing - loaded {len(dog_names)} dogs")
            self.trailing_entry.update_dog_list(dog_names)
            
            # Load locations
            locations = self._get_training_locations()
            # print(f"DEBUG: Trailing - loaded {len(locations)} locations")
            self.trailing_entry.update_location_list(locations)
            
            # Load terrain types
            terrain_types = self._get_terrain_types()
            # print(f"DEBUG: Trailing - loaded {len(terrain_types)} terrain types")
            self.trailing_entry.update_terrain_types(terrain_types)
            
            # Load distraction types
            distraction_types = self._get_distraction_types()
            # print(f"DEBUG: Trailing - loaded {len(distraction_types)} distraction types")
            self.trailing_entry.update_distraction_types(distraction_types)
            
            # Set default handler from config
            trailing_config = self.config.get("trailing", {})
            default_handler = trailing_config.get("default_handler", "")
            if default_handler:
                sv.t_handler.set(default_handler)
            
            # Set last dog from config
            last_dog = trailing_config.get("last_dog", "")
            if last_dog and last_dog in dog_names:
                sv.t_dog.set(last_dog)
                try:
                    next_session = self.get_trailing_next_session_number(last_dog)
                    sv.t_session.set(str(next_session))
                    # Show status message for trailing (queued after air scenting message)
                    self.root.after(1300, lambda: self.show_status_message(
                        f"Trailing ready - {last_dog} - Next session: #{next_session}", "info"))
                except Exception as e:
                    # print(f"Error getting next session number: {e}")
                    pass
            
            # Take form snapshot after data is loaded
            if hasattr(self, 'trailing_entry'):
                self.trailing_entry.take_form_snapshot()
                
        except Exception as e:
            # print(f"Error loading trailing initial data: {e}")
            import traceback
            traceback.print_exc()
    
    # =========================================================================
    # CONFIG PROVIDER METHODS (used by TrailingEntryTab)
    # =========================================================================
    
    def get_handler_name(self):
        """Get the default handler name"""
        return self.config.get("trailing", {}).get("default_handler", "")
    
    def _get_dog_names(self):
        """Get list of dog names from database"""
        from ui_database import get_db_manager
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            return db_mgr.load_dogs()
        except:
            return self.config.get("dog_names", [])
    
    def get_dog_names(self):
        """Alias for _get_dog_names"""
        return self._get_dog_names()
    
    def get_last_dog_name(self):
        """Get the last used dog name"""
        return self.config.get("trailing", {}).get("last_dog", "")
    
    def _get_terrain_types(self):
        """Get terrain types from database, with fallback to defaults"""
        from ui_database import get_db_manager
        from ui_utils import get_default_terrain_types
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            terrain_types = db_mgr.load_terrain_types()
            if not terrain_types:
                terrain_types = self.config.get("terrain_types", [])
            if not terrain_types:
                terrain_types = get_default_terrain_types()
            return terrain_types
        except Exception as e:
            # print(f"Error loading terrain types: {e}")
            terrain_types = self.config.get("terrain_types", [])
            if not terrain_types:
                from ui_utils import get_default_terrain_types
                terrain_types = get_default_terrain_types()
            return terrain_types
    
    def get_terrain_types(self):
        """Alias for _get_terrain_types"""
        return self._get_terrain_types()
    
    def _get_distraction_types(self):
        """Get distraction types from database, with fallback to defaults"""
        from ui_database import get_db_manager
        from ui_utils import get_default_distraction_types
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            distraction_types = db_mgr.load_distraction_types()
            if not distraction_types:
                distraction_types = self.config.get("distraction_types", [])
            if not distraction_types:
                distraction_types = get_default_distraction_types()
            return distraction_types
        except Exception as e:
            # print(f"Error loading distraction types: {e}")
            distraction_types = self.config.get("distraction_types", [])
            if not distraction_types:
                from ui_utils import get_default_distraction_types
                distraction_types = get_default_distraction_types()
            return distraction_types
    
    def get_distraction_types(self):
        """Alias for _get_distraction_types"""
        return self._get_distraction_types()
    
    def _get_training_locations(self):
        """Get training locations from database"""
        from ui_database import get_db_manager
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            return db_mgr.load_locations()
        except:
            return self.config.get("training_locations", [])
    
    def get_training_locations(self):
        """Alias for _get_training_locations"""
        return self._get_training_locations()
