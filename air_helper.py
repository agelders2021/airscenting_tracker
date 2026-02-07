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
Air Scenting Helper Module
Contains helper methods for the Air Scenting Training Session tab.
These methods handle data manipulation, callbacks, and business logic.
"""
import tkinter as tk
from tkinter import messagebox
import sv


class AirScentingHelper:
    """
    Mixin class containing helper methods for Air Scenting tab.
    These methods should be mixed into the main TrainingLoggerUI class.
    """
    
    # =========================================================================
    # SESSION PURPOSE ACCUMULATOR METHODS
    # =========================================================================
    
    def _add_to_purpose_accumulator(self, event):
        """Add selected session purpose to the listbox"""
        purpose = sv.a_purpose.get()
        if purpose:
            current_items = self.a_purpose_listbox.get(0, tk.END)
            if purpose in current_items:
                messagebox.showinfo("Duplicate", f"'{purpose}' is already in the list")
                sv.a_purpose.set("")
                return
            
            self.a_purpose_listbox.insert(tk.END, purpose)
            sv.a_purpose.set("")
            self._update_purpose_scrollbar()
    
    def _remove_purpose_from_list(self, event):
        """Remove session purpose from listbox when double-clicked"""
        selection = self.a_purpose_listbox.curselection()
        if not selection:
            return
        
        purpose = self.a_purpose_listbox.get(selection[0])
        
        if messagebox.askyesno("Remove Session Purpose", f"Remove '{purpose}' from the list?"):
            self.a_purpose_listbox.delete(selection[0])
            self._update_purpose_scrollbar()
    
    def _update_purpose_scrollbar(self):
        """Show or hide purpose scrollbar based on number of items"""
        item_count = self.a_purpose_listbox.size()
        if item_count > 2:
            self.a_purpose_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        else:
            self.a_purpose_scrollbar.pack_forget()
    
    def set_selected_purposes(self, purposes_list):
        """Populate purpose listbox from a list of purpose names"""
        self.a_purpose_listbox.delete(0, tk.END)
        for purpose in purposes_list:
            if purpose and purpose.strip():
                self.a_purpose_listbox.insert(tk.END, purpose.strip())
        self._update_purpose_scrollbar()
    
    def get_selected_purposes(self):
        """Get list of purposes from the listbox"""
        return list(self.a_purpose_listbox.get(0, tk.END))
    
    # =========================================================================
    # TERRAIN ACCUMULATOR METHODS
    # =========================================================================
    
    def add_to_terrain_accumulator(self, event=None):
        """Add selected terrain type to the accumulated terrains list"""
        terrain_type = sv.terrain.get()
        if terrain_type:
            # Check for duplicates
            if terrain_type in self.accumulated_terrains:
                self.show_status_message(f"'{terrain_type}' is already in the list", "info")
                sv.terrain.set("")
                return
            
            # Add to list
            self.accumulated_terrains.append(terrain_type)
            
            # Update combobox values
            self.a_accumulated_terrain_combo['values'] = self.accumulated_terrains
            
            # Enable the combobox if this is the first item
            if len(self.accumulated_terrains) == 1:
                self.a_accumulated_terrain_combo['state'] = 'readonly'
            
            # Display the last (newest) entry
            sv.accumulated_terrain.set(terrain_type)
            
            # Clear selection in add terrain combobox
            sv.terrain.set("")
    
    def remove_terrain_from_list(self, event):
        """Remove terrain type from list when clicked/selected"""
        terrain_type = sv.accumulated_terrain.get()
        if not terrain_type:
            return
        
        # Confirm removal
        if messagebox.askyesno("Remove Terrain Type",
                              f"Remove '{terrain_type}' from the list?"):
            # Find the index of the item being removed
            removed_index = self.accumulated_terrains.index(terrain_type)
            
            # Remove from list
            self.accumulated_terrains.remove(terrain_type)
            
            # Update combobox values
            self.a_accumulated_terrain_combo['values'] = self.accumulated_terrains
            
            # Determine what to display after removal
            if len(self.accumulated_terrains) == 0:
                # List is now empty - show blank and disable combobox
                sv.accumulated_terrain.set("")
                self.a_accumulated_terrain_combo['state'] = 'disabled'
            elif removed_index < len(self.accumulated_terrains):
                # Show the item that's now at the same index (the one that was below)
                sv.accumulated_terrain.set(self.accumulated_terrains[removed_index])
            else:
                # The last item was removed - show the new last item
                sv.accumulated_terrain.set(self.accumulated_terrains[-1])
    
    def set_selected_terrains(self, terrains_list):
        """Populate terrain accumulator from a list of terrain names"""
        self.accumulated_terrains = []
        for terrain in terrains_list:
            if terrain and terrain.strip():
                self.accumulated_terrains.append(terrain.strip())
        
        if hasattr(self, 'a_accumulated_terrain_combo'):
            self.a_accumulated_terrain_combo['values'] = self.accumulated_terrains
            if self.accumulated_terrains:
                self.a_accumulated_terrain_combo['state'] = 'readonly'
                sv.accumulated_terrain.set(self.accumulated_terrains[-1])
            else:
                self.a_accumulated_terrain_combo['state'] = 'disabled'
                sv.accumulated_terrain.set("")
    
    def get_selected_terrains(self):
        """Get list of terrains from the accumulator"""
        return list(self.accumulated_terrains) if hasattr(self, 'accumulated_terrains') else []
    
    # =========================================================================
    # DATE AND DOG CHANGE HANDLERS
    # =========================================================================
    
    def on_date_changed(self, event=None):
        """Update sv.date StringVar when DateEntry changes"""
        date_str = self.a_date_picker.get_date().strftime("%Y-%m-%d")
        sv.date.set(date_str)
    
    def set_date(self, date_string):
        """Set the date in the DateEntry widget"""
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            self.a_date_picker.set_date(date_obj)
            sv.date.set(date_string)
        except (ValueError, AttributeError) as e:
            # print(f"Error setting date: {e}")
            pass
    
    def on_dog_changed(self, event=None):
        """Handle dog selection change - delegate to misc2_ops which saves to database"""
        # Delegate to misc2_ops which handles saving last_dog_name to database
        # and updating session number
        if hasattr(self, 'misc2_ops'):
            self.misc2_ops.on_dog_changed(event)
    
    # =========================================================================
    # SUBJECT RESPONSES METHODS
    # =========================================================================
    
    def add_subject_response(self):
        """Open dialog to add a new subject response"""
        # This would open a dialog for entering subject response details
        # Implementation depends on the SubjectResponseDialog class
        pass
    
    def edit_subject_response(self):
        """Edit the selected subject response"""
        selection = self.a_responses_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a response to edit")
            return
        # Implementation depends on the SubjectResponseDialog class
        pass
    
    def remove_subject_response(self):
        """Remove the selected subject response"""
        selection = self.a_responses_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a response to remove")
            return
        
        if messagebox.askyesno("Confirm Remove", "Remove the selected response?"):
            self.a_responses_tree.delete(selection[0])
    
    # =========================================================================
    # DATA REFRESH METHODS
    # =========================================================================
    
    def refresh_location_list(self):
        """Refresh the location combobox from database"""
        from ui_database import get_db_manager
        
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            locations = db_mgr.load_locations()
            if hasattr(self, 'a_location_combo'):
                self.a_location_combo['values'] = sorted(locations) if locations else []
        except Exception as e:
            # print(f"Error refreshing location list: {e}")
            pass
    
    def refresh_terrain_list(self):
        """Refresh the terrain combobox from database"""
        from ui_database import get_db_manager
        
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            terrain_types = db_mgr.load_terrain_types()
            if hasattr(self, 'a_terrain_combo'):
                self.a_terrain_combo['values'] = terrain_types if terrain_types else []
        except Exception as e:
            # print(f"Error refreshing terrain list: {e}")
            pass
    
    def refresh_dog_list(self):
        """Refresh the dog combobox from database"""
        from ui_database import get_db_manager
        
        try:
            db_mgr = get_db_manager(sv.db_type.get())
            dogs = db_mgr.load_dogs()
            if hasattr(self, 'a_dog_combo'):
                self.a_dog_combo['values'] = dogs if dogs else []
        except Exception as e:
            # print(f"Error refreshing dog list: {e}")
            pass
    
    # =========================================================================
    # SAVE BUTTON TEXT
    # =========================================================================
    
    def set_save_button_text(self, text):
        """Update the save button text (for Save vs Update mode)"""
        if hasattr(self, 'a_save_session_btn'):
            self.a_save_session_btn.config(text=text)
    
    # =========================================================================
    # SUBJECT RESPONSES GRID METHODS
    # =========================================================================
    
    def update_subject_responses_grid(self, event=None):
        """Update subject responses grid - enable/disable rows based on Subjects Found value"""
        subjects_found = sv.subjects_found.get()
        
        # Parse subjects found value (e.g., "2 out of 3" -> 2 found)
        num_found = 0
        if subjects_found and " out of " in subjects_found:
            try:
                num_found = int(subjects_found.split(" out of ")[0])
            except:
                pass
        
        # Update tags on all 10 rows - enable those within num_found, disable others
        for i in range(1, 11):
            item_id = f'subject_{i}'
            # Determine odd/even tag for this row
            row_tag = 'odd' if i % 2 == 1 else 'even'
            
            if i <= num_found:
                # Enable this row (keep odd/even tag for background shading)
                self.a_subject_responses_tree.item(item_id, tags=(row_tag, 'enabled'))
            else:
                # Disable this row and clear values (keep odd/even tag for background shading)
                self.a_subject_responses_tree.item(item_id, values=(f'Subject {i}', '', ''), tags=(row_tag, 'disabled'))
    
    # =========================================================================
    # TREEVIEW EDITING METHODS (for Subject Responses)
    # =========================================================================
    
    def on_treeview_click(self, event):
        """Handle click on treeview - show inline combobox for TFR/Re-find columns"""
        # Identify what was clicked
        region = self.a_subject_responses_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        
        item = self.a_subject_responses_tree.identify_row(event.y)
        column = self.a_subject_responses_tree.identify_column(event.x)
        
        if not item or not column:
            return
        
        # Check if row is enabled
        tags = self.a_subject_responses_tree.item(item, 'tags')
        if 'disabled' in tags:
            return  # Don't allow editing disabled rows
        
        # Determine which column was clicked (column is like '#1', '#2', '#3')
        col_index = int(column.replace('#', ''))
        
        # Only allow editing TFR (column 2) and Re-find (column 3)
        if col_index not in [2, 3]:
            return
        
        # Close any existing edit combobox
        self.close_tree_edit()
        
        # Get the bounding box of the cell
        bbox = self.a_subject_responses_tree.bbox(item, column)
        if not bbox:
            return
        x, y, width, height = bbox
        
        # Get current values
        values = list(self.a_subject_responses_tree.item(item, 'values'))
        current_value = values[col_index - 1] if col_index <= len(values) else ''
        
        # Determine options based on column
        if col_index == 2:  # TFR column
            options = self.tfr_options
        else:  # Re-find column
            options = self.refind_options
        
        # Create combobox positioned over the cell
        from tkinter import ttk
        self.a_tree_edit_combo = ttk.Combobox(
            self.a_subject_responses_tree,
            values=options,
            state='readonly'
        )
        self.a_tree_edit_combo.set(current_value)
        
        # Position the combobox
        self.a_tree_edit_combo.place(x=x, y=y, width=width, height=height)
        
        # Store editing context
        self.tree_edit_item = item
        self.tree_edit_column = col_index
        
        # Bind events
        self.a_tree_edit_combo.bind('<<ComboboxSelected>>', self.on_tree_edit_select)
        self.a_tree_edit_combo.bind('<FocusOut>', lambda e: self.close_tree_edit())
        self.a_tree_edit_combo.bind('<Escape>', lambda e: self.close_tree_edit())
        
        # Focus and open dropdown
        self.a_tree_edit_combo.focus_set()
        self.a_tree_edit_combo.event_generate('<Button-1>')
    
    def on_tree_edit_select(self, event=None):
        """Handle selection in inline edit combobox"""
        if not self.a_tree_edit_combo or not self.tree_edit_item:
            return
        
        # Get the new value
        new_value = self.a_tree_edit_combo.get()
        
        # Update the treeview
        values = list(self.a_subject_responses_tree.item(self.tree_edit_item, 'values'))
        values[self.tree_edit_column - 1] = new_value
        self.a_subject_responses_tree.item(self.tree_edit_item, values=values)
        
        # Close the combobox
        self.close_tree_edit()
    
    def close_tree_edit(self):
        """Close the inline edit combobox"""
        if hasattr(self, 'a_tree_edit_combo') and self.a_tree_edit_combo:
            self.a_tree_edit_combo.destroy()
            self.a_tree_edit_combo = None
        self.tree_edit_item = None
        self.tree_edit_column = None
    
    def reset_subject_responses_tree_selection(self):
        """Reset tree selection and scroll to subject 1"""
        if hasattr(self, 'a_subject_responses_tree'):
            # Clear any current selection
            self.a_subject_responses_tree.selection_remove(self.a_subject_responses_tree.selection())
            
            # Select subject 1 (first item)
            first_item = 'subject_1'
            if self.a_subject_responses_tree.exists(first_item):
                self.a_subject_responses_tree.selection_set(first_item)
                self.a_subject_responses_tree.see(first_item)
    
    # =========================================================================
    # TIME PICKER METHODS
    # =========================================================================
    
    def _on_start_time_changed(self):
        """Handle start time picker change - update the start_time StringVar in HH:MM format"""
        # Get time from picker as tuple (hours, minutes)
        hours = self.a_start_time_picker.hours24()
        minutes = self.a_start_time_picker.minutes()
        # Format as HH:MM (e.g., 14:36 for 2:36 PM)
        time_str = f"{hours:02d}:{minutes:02d}"
        sv.start_time.set(time_str)
    
    def _on_finish_time_changed(self):
        """Handle finish time picker change - update the finish_time StringVar in HH:MM format"""
        # Get time from picker as tuple (hours, minutes)
        hours = self.a_finish_time_picker.hours24()
        minutes = self.a_finish_time_picker.minutes()
        # Format as HH:MM (e.g., 14:36 for 2:36 PM)
        time_str = f"{hours:02d}:{minutes:02d}"
        sv.finish_time.set(time_str)
    
    def _setup_timepicker_wheel(self, time_picker, frame, picker_type):
        """
        Setup mouse wheel handling for the time picker.
        
        When hovering over hours, wheel adjusts hours.
        When hovering over minutes, wheel adjusts minutes.
        When not over the picker widgets, wheel scrolls the window.
        
        Args:
            time_picker: The SpinTimePickerModern instance
            frame: The frame containing the time picker
            picker_type: 'start' or 'finish' to identify which picker
        """
        import platform
        
        # Get references to the hour and minute SpinLabel widgets
        hours_widget = time_picker._24HrsTime  # Using 24hr format
        minutes_widget = time_picker._minutes
        
        def adjust_spinlabel(widget, delta):
            """Adjust a SpinLabel value by delta (positive = increment, negative = decrement)"""
            # Access the internal attributes of SpinLabel
            number_lst = widget.number_lst
            current_index = widget._current_index
            
            if delta > 0:
                # Scroll up - increment
                if current_index < len(number_lst) - 1:
                    widget._current_index += 1
                else:
                    widget._current_index = 0
            else:
                # Scroll down - decrement
                if current_index > 0:
                    widget._current_index -= 1
                else:
                    widget._current_index = len(number_lst) - 1
            
            widget.current_val = number_lst[widget._current_index]
            widget.updateLabel()
        
        def on_hours_wheel(event):
            """Handle wheel events on hours widget"""
            if platform.system() == 'Linux':
                delta = 1 if event.num == 4 else -1
            else:
                delta = 1 if event.delta > 0 else -1
            adjust_spinlabel(hours_widget, delta)
            if picker_type == 'start':
                self._on_start_time_changed()
            else:
                self._on_finish_time_changed()
            return "break"
        
        def on_minutes_wheel(event):
            """Handle wheel events on minutes widget"""
            if platform.system() == 'Linux':
                delta = 1 if event.num == 4 else -1
            else:
                delta = 1 if event.delta > 0 else -1
            adjust_spinlabel(minutes_widget, delta)
            if picker_type == 'start':
                self._on_start_time_changed()
            else:
                self._on_finish_time_changed()
            return "break"
        
        def on_frame_wheel(event):
            """Handle wheel events on the frame (not on hours/minutes) - block propagation"""
            # Just block propagation, don't do anything
            return "break"
        
        # Bind wheel events to hours widget
        if platform.system() == 'Linux':
            hours_widget.bind("<Button-4>", on_hours_wheel)
            hours_widget.bind("<Button-5>", on_hours_wheel)
            minutes_widget.bind("<Button-4>", on_minutes_wheel)
            minutes_widget.bind("<Button-5>", on_minutes_wheel)
            # Block wheel on the frame and separator to prevent window scroll
            frame.bind("<Button-4>", on_frame_wheel)
            frame.bind("<Button-5>", on_frame_wheel)
            time_picker.bind("<Button-4>", on_frame_wheel)
            time_picker.bind("<Button-5>", on_frame_wheel)
            time_picker._separator.bind("<Button-4>", on_frame_wheel)
            time_picker._separator.bind("<Button-5>", on_frame_wheel)
        else:
            hours_widget.bind("<MouseWheel>", on_hours_wheel)
            minutes_widget.bind("<MouseWheel>", on_minutes_wheel)
            # Block wheel on the frame and separator to prevent window scroll
            frame.bind("<MouseWheel>", on_frame_wheel)
            time_picker.bind("<MouseWheel>", on_frame_wheel)
            time_picker._separator.bind("<MouseWheel>", on_frame_wheel)
