#!/usr/bin/env python3
"""
Phase 1.86 Migration: Add Missing Delete/Undelete Methods

This script adds the delete_current_session() and undelete_current_session()
methods that were missing from Phase 1.80.

Changes:
1. Add delete_current_session() to ui_navigation.py
2. Add undelete_current_session() to ui_navigation.py
3. Add enable_delete_undelete_buttons() to ui_navigation.py
4. Add disable_delete_undelete_buttons() to ui_navigation.py
5. Update load_session_by_number() to enable buttons

Usage:
    python migrate_phase1_86_add_delete_methods.py          # Show what will be done
    python migrate_phase1_86_add_delete_methods.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase1_86_AddDeleteMethodsMigration:
    """Phase 1.86: Add missing delete/undelete methods"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Add delete/undelete methods and enable/disable helpers"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 1.86: ADD MISSING DELETE/UNDELETE METHODS")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Add to ui_navigation.py:")
        print("   - enable_delete_undelete_buttons()")
        print("   - disable_delete_undelete_buttons()")
        print("   - delete_current_session()")
        print("   - undelete_current_session()")
        print()
        print("2. Update load_session_by_number():")
        print("   - Call enable_delete_undelete_buttons() after loading")
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
    
    def modify_ui_navigation(self):
        """Add delete/undelete methods to ui_navigation.py"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success = True
            
            # Add methods before on_status_filter_changed
            insertion_point = "    def on_status_filter_changed(self):"
            
            new_methods = '''    def enable_delete_undelete_buttons(self):
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
            f"Mark session #{session_num} for {dog_name} as deleted?\\n\\n"
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
    
    '''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_methods + insertion_point)
                print("  ✓ Added delete/undelete helper methods")
            else:
                print("  ✗ Could not find insertion point")
                success = False
            
            # Update load_session_by_number to enable buttons
            old_load_end = '''            sv.status.set(f"Loaded session #{session_number} for {dog_name}")
            
            # Update navigation buttons
            self.update_navigation_buttons()'''
            
            new_load_end = '''            sv.status.set(f"Loaded session #{session_number} for {dog_name}")
            
            # Enable delete/undelete buttons (editing existing session)
            self.enable_delete_undelete_buttons()
            
            # Update navigation buttons
            self.update_navigation_buttons()'''
            
            if old_load_end in content:
                content = content.replace(old_load_end, new_load_end)
                print("  ✓ Updated load_session_by_number() to enable buttons")
            else:
                print("  ✗ Could not find load_session_by_number() end pattern")
                success = False
            
            if success:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return success
        else:
            print("  - Would add enable_delete_undelete_buttons() method")
            print("  - Would add disable_delete_undelete_buttons() method")
            print("  - Would add delete_current_session() method")
            print("  - Would add undelete_current_session() method")
            print("  - Would update load_session_by_number() to enable buttons")
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
        results.append(self.modify_ui_navigation())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 1.86 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Added enable_delete_undelete_buttons() method")
            print("  ✓ Added disable_delete_undelete_buttons() method")
            print("  ✓ Added delete_current_session() method")
            print("  ✓ Added undelete_current_session() method")
            print("  ✓ Updated load_session_by_number() to enable buttons")
            print("  ✓ Migration script backed up")
            print()
            print("TEST IT:")
            print("  1. Load an existing session")
            print("  2. Delete/Undelete buttons should be enabled")
            print("  3. Click 'Delete' to mark as deleted")
            print("  4. Click 'Undelete' to restore to active")
            print("  5. Click 'New' - buttons should be disabled")
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
    
    migration = Phase1_86_AddDeleteMethodsMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
