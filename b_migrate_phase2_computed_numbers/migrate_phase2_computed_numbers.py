#!/usr/bin/env python3
"""
Phase 2 Migration: Display Computed Session Numbers

This script implements Phase 2 of the session number migration:
1. Display computed session numbers instead of database session_number
2. Update "Session Information" title based on status:
   - Active: "Session Information" (black, normal)
   - Deleted: "Session Information *** MARKED DELETED ***" (red, bold)
3. Enable Delete button only for active sessions
4. Enable Undelete button only for deleted sessions
5. Reload session after delete/undelete to update display

Changes:
1. ui.py - Store reference to session_frame LabelFrame
2. ui_navigation.py - Update load_session_by_number() to compute and display ordinal number
3. ui_navigation.py - Update LabelFrame title and button states based on status
4. ui_navigation.py - Reload session after delete/undelete

Usage:
    python migrate_phase2_computed_numbers.py          # Show what will be done
    python migrate_phase2_computed_numbers.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2ComputedNumbersMigration:
    """Phase 2: Display computed session numbers"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui.py": "Store reference to session_frame LabelFrame",
            "ui_navigation.py": "Display computed numbers and update UI based on status",
            "ui_database.py": "Add get_session_status method"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2: DISPLAY COMPUTED SESSION NUMBERS")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Store session_frame reference in ui.py")
        print("   - Allows updating LabelFrame title from navigation code")
        print()
        print("2. Update load_session_by_number() in ui_navigation.py:")
        print("   - Compute ordinal session number based on filter")
        print("   - Display computed number (not database number)")
        print("   - Update LabelFrame title based on status:")
        print("     • Active: 'Session Information' (black)")
        print("     • Deleted: 'Session Information *** MARKED DELETED ***' (red, bold)")
        print("   - Enable Delete button only for active sessions")
        print("   - Enable Undelete button only for deleted sessions")
        print()
        print("3. Update delete/undelete methods:")
        print("   - Reload session after status change")
        print()
        print("4. Add get_session_status() to ui_database.py")
        print()
        print("FILES TO BE MODIFIED:")
        for filename, description in self.files_to_modify.items():
            filepath = os.path.join(self.project_dir, filename)
            exists = "✓" if os.path.exists(filepath) else "✗ NOT FOUND"
            print(f"  {exists} {filename}")
            print(f"      {description}")
        print()
        if self.execute:
            print(f"BACKUPS: Original files will be copied to {self.backup_folder}/")
            print(f"         Migration script will also be copied to {self.backup_folder}/")
            print()
    
    def create_backup_folder(self):
        """Create backup folder if it doesn't exist"""
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)
            print(f"Created backup folder: {self.backup_folder}")
    
    def backup_file(self, filepath):
        """Copy file to backup folder"""
        self.create_backup_folder()
        filename = os.path.basename(filepath)
        backup_path = os.path.join(self.backup_folder, filename)
        shutil.copy2(filepath, backup_path)
        print(f"  ✓ Backed up: {filename} -> {self.backup_folder}/{filename}")
    
    def backup_script(self):
        """Copy this migration script to backup folder"""
        self.create_backup_folder()
        script_path = os.path.abspath(sys.argv[0])
        script_name = os.path.basename(script_path)
        backup_path = os.path.join(self.backup_folder, script_name)
        shutil.copy2(script_path, backup_path)
        print(f"  ✓ Backed up migration script: {script_name} -> {self.backup_folder}/{script_name}")
    
    def modify_ui(self):
        """Store reference to session_frame in ui.py"""
        print("\n[1/3] Modifying ui.py...")
        
        filepath = os.path.join(self.project_dir, "ui.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find session_frame creation and store reference
            old_frame = '''        # Session Information
        session_frame = tk.LabelFrame(frame, text="Session Information", padx=10, pady=5)
        session_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)'''
            
            new_frame = '''        # Session Information
        self.a_session_frame = tk.LabelFrame(frame, text="Session Information", padx=10, pady=5)
        self.a_session_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        session_frame = self.a_session_frame  # Alias for compatibility'''
            
            if old_frame in content:
                content = content.replace(old_frame, new_frame)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Stored reference to session_frame as self.a_session_frame")
                return True
            else:
                print("  ✗ Could not find session_frame pattern")
                return False
        else:
            print("  - Would store session_frame reference as self.a_session_frame")
            return True
    
    def modify_ui_database(self):
        """Add get_session_status method to ui_database.py"""
        print("\n[2/3] Modifying ui_database.py...")
        
        filepath = os.path.join(self.project_dir, "ui_database.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add method after update_session_status in DatabaseManager
            insertion_point = '''            print(f"Error updating session status: {e}")
            return False
    
    def compute_session_number(self, dog_name, session_date, status_filter='active'):'''
            
            new_method = '''            print(f"Error updating session status: {e}")
            return False
    
    def get_session_status(self, session_number, dog_name):
        """Get the status of a specific session
        
        Args:
            session_number: Session number (database value)
            dog_name: Dog name
        
        Returns:
            str: 'active', 'deleted', or None if not found
        """
        if not dog_name or not dog_name.strip():
            return None
        
        dog_name = dog_name.strip()
        
        try:
            with get_connection() as conn:
                result = conn.execute(
                    text("""
                        SELECT status 
                        FROM training_sessions 
                        WHERE session_number = :session_number AND dog_name = :dog_name
                    """),
                    {"session_number": session_number, "dog_name": dog_name}
                )
                row = result.fetchone()
            
            if row:
                # Return status, defaulting to 'active' if NULL
                return row[0] if row[0] else 'active'
            return None
            
        except Exception as e:
            print(f"Error getting session status: {e}")
            return None
    
    def compute_session_number(self, dog_name, session_date, status_filter='active'):'''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_method)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Added get_session_status() method")
                return True
            else:
                print("  ✗ Could not find insertion point")
                return False
        else:
            print("  - Would add get_session_status() method")
            return True
    
    def modify_ui_navigation(self):
        """Update navigation to display computed numbers and update UI"""
        print("\n[3/3] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success = True
            
            # 1. Add method to update session frame title
            insertion_point = "    def enable_delete_undelete_buttons(self):"
            
            new_method = '''    def update_session_frame_title(self, status):
        """Update the Session Information LabelFrame title based on status
        
        Args:
            status: 'active', 'deleted', or None
        """
        if hasattr(self.ui, 'a_session_frame'):
            if status == 'deleted':
                self.ui.a_session_frame.config(
                    text="Session Information *** MARKED DELETED ***",
                    foreground="red",
                    font=("TkDefaultFont", 9, "bold")
                )
            else:
                # Active or None (treat NULL as active)
                self.ui.a_session_frame.config(
                    text="Session Information",
                    foreground="black",
                    font=("TkDefaultFont", 9)
                )
    
    '''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_method + insertion_point)
                print("  ✓ Added update_session_frame_title() method")
            else:
                print("  ✗ Could not find insertion point for update_session_frame_title()")
                success = False
            
            # 2. Update load_session_by_number to compute and display ordinal number
            old_load = '''            # Enable delete/undelete buttons (editing existing session)
            self.enable_delete_undelete_buttons()
            
            sv.status.set(f"Loaded session #{session_number}")'''
            
            new_load = '''            # Get session status and compute ordinal position
            session_status = db_ops.get_session_status(session_number, dog_name)
            status_filter = sv.session_status_filter.get()
            
            # Compute ordinal session number based on current filter
            computed_number = db_ops.compute_session_number(dog_name, session_dict["date"], status_filter)
            
            # Display computed number (not database session_number)
            sv.session_number.set(str(computed_number))
            
            # Update session frame title based on status
            self.update_session_frame_title(session_status)
            
            # Enable/disable delete/undelete buttons based on status
            if session_status == 'deleted':
                # Deleted session - disable Delete, enable Undelete
                if hasattr(self.ui, 'a_delete_undelete_frame'):
                    for child in self.ui.a_delete_undelete_frame.winfo_children():
                        button_text = child.cget('text')
                        if button_text == 'Delete':
                            child.config(state="disabled")
                        elif button_text == 'Undelete':
                            child.config(state="normal")
            else:
                # Active session - enable Delete, disable Undelete
                if hasattr(self.ui, 'a_delete_undelete_frame'):
                    for child in self.ui.a_delete_undelete_frame.winfo_children():
                        button_text = child.cget('text')
                        if button_text == 'Delete':
                            child.config(state="normal")
                        elif button_text == 'Undelete':
                            child.config(state="disabled")
            
            sv.status.set(f"Loaded session (computed #{computed_number})")'''
            
            if old_load in content:
                content = content.replace(old_load, new_load)
                print("  ✓ Updated load_session_by_number() to display computed numbers")
            else:
                print("  ✗ Could not find load_session_by_number() pattern")
                success = False
            
            # 3. Update delete_current_session to reload session
            old_delete_end = '''                # Refresh navigation to reflect filter
                self.update_navigation_buttons()'''
            
            new_delete_end = '''                # Reload session to update display
                self.load_session_by_number(session_num)'''
            
            if old_delete_end in content:
                content = content.replace(old_delete_end, new_delete_end)
                print("  ✓ Updated delete_current_session() to reload session")
            else:
                print("  ✗ Could not find delete_current_session() pattern")
                success = False
            
            # 4. Update undelete_current_session to reload session
            old_undelete_end = '''                # Refresh navigation to reflect filter
                self.update_navigation_buttons()
            else:
                messagebox.showerror("Error", "Failed to restore session")'''
            
            new_undelete_end = '''                # Reload session to update display
                self.load_session_by_number(session_num)
            else:
                messagebox.showerror("Error", "Failed to restore session")'''
            
            if old_undelete_end in content:
                content = content.replace(old_undelete_end, new_undelete_end)
                print("  ✓ Updated undelete_current_session() to reload session")
            else:
                print("  ✗ Could not find undelete_current_session() pattern")
                success = False
            
            if success:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return success
        else:
            print("  - Would add update_session_frame_title() method")
            print("  - Would update load_session_by_number() to compute and display numbers")
            print("  - Would update delete_current_session() to reload session")
            print("  - Would update undelete_current_session() to reload session")
            return True
    
    def run(self):
        """Execute the migration"""
        self.print_header()
        self.print_changes()
        
        if not self.execute:
            print("=" * 80)
            print("DRY RUN - No changes made")
            print("=" * 80)
            print()
            print("To execute this migration, run:")
            print(f"  python {os.path.basename(sys.argv[0])} --execute")
            print()
            return True
        
        print("=" * 80)
        print("EXECUTING MIGRATION")
        print("=" * 80)
        print()
        
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("\nMigration cancelled.")
            return False
        
        print("\nProceeding with migration...\n")
        
        # Backup the migration script itself first
        self.backup_script()
        print()
        
        results = []
        results.append(self.modify_ui())
        results.append(self.modify_ui_database())
        results.append(self.modify_ui_navigation())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 2 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Stored session_frame reference for title updates")
            print("  ✓ Added get_session_status() method")
            print("  ✓ Sessions now display computed ordinal numbers")
            print("  ✓ LabelFrame title updates based on status")
            print("  ✓ Delete button disabled for deleted sessions")
            print("  ✓ Undelete button disabled for active sessions")
            print("  ✓ Migration script backed up")
            print()
            print("TEST IT:")
            print("  1. Load an active session")
            print("     - Title: 'Session Information' (black)")
            print("     - Delete enabled, Undelete disabled")
            print("  2. Click Delete")
            print("     - Title: 'Session Information *** MARKED DELETED ***' (red, bold)")
            print("     - Delete disabled, Undelete enabled")
            print("  3. Switch filters - session numbers recompute")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Some patterns could not be found.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase2ComputedNumbersMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
