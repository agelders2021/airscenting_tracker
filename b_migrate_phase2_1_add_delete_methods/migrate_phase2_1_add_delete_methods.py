#!/usr/bin/env python3
"""
Phase 2.1 Migration: Add delete_current_session and undelete_current_session

These methods were supposed to be added in Phase 1.88 but are missing.
This script adds them WITH the Phase 2 reload functionality built in.

Changes:
1. Add delete_current_session() - marks session deleted and reloads
2. Add undelete_current_session() - marks session active and reloads

Usage:
    python migrate_phase2_1_add_delete_methods.py          # Show what will be done
    python migrate_phase2_1_add_delete_methods.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_1_AddDeleteMethodsMigration:
    """Phase 2.1: Add missing delete/undelete methods"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Add delete_current_session and undelete_current_session"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.1: ADD DELETE/UNDELETE METHODS WITH RELOAD")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Add delete_current_session() to ui_navigation.py:")
        print("   - Confirms with user")
        print("   - Marks session as deleted")
        print("   - Reloads session to update display")
        print()
        print("2. Add undelete_current_session() to ui_navigation.py:")
        print("   - Confirms with user")
        print("   - Marks session as active")
        print("   - Reloads session to update display")
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
            
            # Add methods before on_status_filter_changed
            insertion_point = "    def on_status_filter_changed(self):"
            
            new_methods = '''    def delete_current_session(self):
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
            f"Mark this session for {dog_name} as deleted?\\n\\n"
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
    
    '''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_methods + insertion_point)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Added delete_current_session() method")
                print("  ✓ Added undelete_current_session() method")
                return True
            else:
                print("  ✗ Could not find insertion point")
                return False
        else:
            print("  - Would add delete_current_session() method")
            print("  - Would add undelete_current_session() method")
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
            print("PHASE 2.1 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Added delete_current_session() method")
            print("  ✓ Added undelete_current_session() method")
            print("  ✓ Both methods reload session after updating status")
            print("  ✓ Migration script backed up")
            print()
            print("NOTE:")
            print("  One more step needed - Phase 2.2 will update load_session_by_number()")
            print("  to store the database session_number for delete/undelete to use")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Could not find insertion point.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase2_1_AddDeleteMethodsMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
