"""
File Operations Module for Air-Scenting Logger
Handles file/folder selection, drag-drop, and file management
"""
import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox


class FileOperations:
    """Manages all file and folder operations for the application"""
    
    def __init__(self, ui):
        """
        Initialize with reference to main UI
        
        Args:
            ui: Reference to AirScentingUI instance
        """
        self.ui = ui
    
    # ========================================
    # FOLDER SELECTION METHODS
    # ========================================
    
    def select_db_folder(self):
        """Select database folder"""
        folder = filedialog.askdirectory(title="Select Database Folder")
        if folder:
            from sv import sv
            sv.db_path.set(folder)
            self.ui.machine_db_path = folder
    
    def select_folder(self):
        """Select trail maps folder"""
        folder = filedialog.askdirectory(title="Select Trail Maps Storage Folder")
        if folder:
            from sv import sv
            sv.trail_maps_folder.set(folder)
            self.ui.machine_trail_maps_folder = folder
    
    def select_backup_folder(self):
        """Select backup folder"""
        folder = filedialog.askdirectory(title="Select Backup Folder")
        if folder:
            from sv import sv
            sv.backup_folder.set(folder)
            self.ui.machine_backup_folder = folder
    
    # ========================================
    # DRAG & DROP HANDLERS
    # ========================================
    
    def drag_enter(self, event):
        """Visual feedback when dragging over drop zone"""
        self.ui.drop_label.configure(bg="#90EE90")
    
    def drag_leave(self, event):
        """Reset visual feedback"""
        self.ui.drop_label.configure(bg="#e0e0e0")
    
    def handle_drop(self, event):
        """Handle dropped files (supports multiple) - copies to trail maps folder"""
        from sv import sv
        
        self.ui.drop_label.configure(bg="#e0e0e0")
        
        # Check if trail maps folder is configured
        trail_maps_folder = sv.trail_maps_folder.get().strip()
        if not trail_maps_folder or not os.path.exists(trail_maps_folder):
            messagebox.showerror(
                "Trail Maps Folder Not Set",
                "Please configure the Trail Maps Storage Folder in the Setup tab first."
            )
            return
        
        # Check if dog is selected (needed for unique filename)
        if not sv.dog.get():
            messagebox.showwarning(
                "No Dog Selected",
                "Please select a dog before adding maps/images.\n\n"
                "The dog name is used to organize files."
            )
            return
        
        dog_name = sv.dog.get()
        session_number = sv.session_number.get()
        
        # Parse dropped data - can be multiple files
        data = event.data.strip()
        
        # Split by whitespace but respect curly braces grouping
        filepaths = []
        if data.startswith("{"):
            # Multiple files with curly braces
            parts = data.split("} {")
            for part in parts:
                part = part.strip("{}")
                if part:
                    filepaths.append(part)
        else:
            # Single file or space-separated files
            filepaths = [data]
        
        # Process each file
        copied_files = []
        import re
        
        for filepath in filepaths:
            filepath = filepath.strip()
            if os.path.exists(filepath):
                ext = os.path.splitext(filepath)[1].lower()
                if ext in ['.pdf', '.jpg', '.jpeg', '.png']:
                    # Create unique filename: {dog}_{session}_{timestamp}_{original}
                    original_name = os.path.basename(filepath)
                    # Sanitize dog name for filename
                    safe_dog_name = re.sub(r'[^\w\-]', '_', dog_name)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    unique_name = f"{safe_dog_name}_session{session_number}_{timestamp}_{original_name}"
                    
                    # Copy file to trail maps folder
                    dest_path = os.path.join(trail_maps_folder, unique_name)
                    try:
                        shutil.copy2(filepath, dest_path)
                        copied_files.append(unique_name)  # Store just the filename, not full path
                    except Exception as e:
                        messagebox.showerror("Copy Error", f"Failed to copy {original_name}:\n{e}")
        
        if copied_files:
            # Add to list (don't replace, accumulate)
            self.ui.map_files_list.extend(copied_files)
            # Remove duplicates while preserving order
            seen = set()
            self.ui.map_files_list = [x for x in self.ui.map_files_list if not (x in seen or seen.add(x))]
            
            # Update listbox
            self.ui.map_listbox.delete(0, "end")
            for filename in self.ui.map_files_list:
                self.ui.map_listbox.insert("end", filename)
            
            # Enable view and delete buttons
            self.ui.view_map_button.config(state="normal")
            self.ui.delete_map_button.config(state="normal")
            
            sv.status.set(f"{len(copied_files)} file(s) copied to trail maps folder")
        else:
            messagebox.showerror("Error", "Only PDF, JPG, and PNG files supported!")
    
    # ========================================
    # FILE VIEWING AND DELETION
    # ========================================
    
    def view_selected_map(self):
        """Open the selected map/image file from trail maps folder"""
        from sv import sv
        
        selection = self.ui.map_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a file from the list to view")
            return
        
        # Get the filename from map_files_list using the index
        selected_index = selection[0]
        if selected_index < len(self.ui.map_files_list):
            filename = self.ui.map_files_list[selected_index]
            
            # Build full path from trail maps folder
            trail_maps_folder = sv.trail_maps_folder.get().strip()
            if trail_maps_folder:
                filepath = os.path.join(trail_maps_folder, filename)
            else:
                filepath = filename
            
            self.open_external_file(filepath)
    
    def delete_selected_map(self):
        """Delete the selected map/image file from trail maps folder"""
        from sv import sv
        
        selection = self.ui.map_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a file from the list to delete")
            return
        
        selected_index = selection[0]
        if selected_index >= len(self.ui.map_files_list):
            return
        
        filename = self.ui.map_files_list[selected_index]
        
        # Warning dialog
        result = messagebox.askokcancel(
            "Delete Map/Image",
            f"Are you sure you want to delete '{filename}'?\n\nThis operation cannot be reversed.",
            icon='warning'
        )
        
        if not result:
            return
        
        # Delete the actual file from trail maps folder
        try:
            trail_maps_folder = sv.trail_maps_folder.get().strip()
            if trail_maps_folder:
                full_path = os.path.join(trail_maps_folder, filename)
            else:
                full_path = filename
            
            if os.path.exists(full_path):
                os.remove(full_path)
                sv.status.set(f"Deleted file: {filename}")
            else:
                sv.status.set(f"Removed from list (file not found): {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete file:\n{str(e)}")
            return
        
        # Remove from list and listbox
        self.ui.map_files_list.pop(selected_index)
        self.ui.map_listbox.delete(selected_index)
        
        # Update button states
        if not self.ui.map_files_list:
            self.ui.view_map_button.config(state="disabled")
            self.ui.delete_map_button.config(state="disabled")
    
    def open_external_file(self, file_path):
        """Open a file (PDF, image, etc.) with the system's default application"""
        from sv import sv
        
        if not file_path or file_path == '':
            messagebox.showwarning("No File", "No file path specified")
            return
        
        # Convert to Path object
        path = Path(file_path)
        
        # If path is relative, try to find it in the trail maps folder
        if not path.is_absolute():
            possible_paths = []
            
            # Try trail maps folder from config first
            trail_maps_folder = sv.trail_maps_folder.get()
            if trail_maps_folder and os.path.exists(trail_maps_folder):
                possible_paths.append(Path(trail_maps_folder) / file_path)
            
            # Try as-is
            possible_paths.append(path)
            
            # Find first existing path
            found_path = None
            for p in possible_paths:
                if p.exists():
                    found_path = p
                    break
            
            if found_path:
                path = found_path
            else:
                error_msg = f"Could not find file: {file_path}\n\nSearched in:\n"
                for p in possible_paths:
                    error_msg += f"  • {p}\n"
                error_msg += "\nTip: Check your trail maps folder setting in Setup tab."
                messagebox.showerror("File Not Found", error_msg)
                return
        
        if not path.exists():
            messagebox.showerror("File Not Found", f"Could not find file:\n{path}")
            return
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS or Linux
                import subprocess
                import platform
                if platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', path])
                else:  # Linux
                    subprocess.run(['xdg-open', path])
        except Exception as e:
            messagebox.showerror("Error Opening File", 
                               f"Could not open file:\n{path}\n\nError: {str(e)}")
