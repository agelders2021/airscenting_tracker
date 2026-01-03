#!/usr/bin/env python3
"""
Phase 2.2 Migration: Store Database Session Number

This script updates load_session_by_number() to store the database session_number
so that delete/undelete methods know which session to update.

Changes:
1. Store session_number parameter as self.current_db_session_number in load_session_by_number()

Usage:
    python migrate_phase2_2_store_db_session.py          # Show what will be done
    python migrate_phase2_2_store_db_session.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_2_StoreDbSessionMigration:
    """Phase 2.2: Store database session number"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Store database session_number when loading"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.2: STORE DATABASE SESSION NUMBER")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Update load_session_by_number() in ui_navigation.py:")
        print("   - Store session_number parameter as self.current_db_session_number")
        print("   - Delete/undelete methods will use this to update correct session")
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
        """Update load_session_by_number to store database session_number"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add line at start of load_session_by_number to store the db session number
            old_start = '''    def load_session_by_number(self, session_number):
        """Load session data from database by session number and current dog"""
        from sv import sv
        from ui_database import DatabaseOperations
        from ui_form_management import FormManagement
        import json
        import tkinter as tk
        
        dog_name = sv.dog.get().strip() if sv.dog.get() else ""'''
            
            new_start = '''    def load_session_by_number(self, session_number):
        """Load session data from database by session number and current dog"""
        from sv import sv
        from ui_database import DatabaseOperations
        from ui_form_management import FormManagement
        import json
        import tkinter as tk
        
        # Store database session number for delete/undelete operations
        self.current_db_session_number = session_number
        
        dog_name = sv.dog.get().strip() if sv.dog.get() else ""'''
            
            if old_start in content:
                content = content.replace(old_start, new_start)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Updated load_session_by_number() to store database session_number")
                return True
            else:
                print("  ✗ Could not find load_session_by_number() start pattern")
                return False
        else:
            print("  - Would update load_session_by_number() to store database session_number")
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
            print("PHASE 2.2 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ load_session_by_number() now stores database session_number")
            print("  ✓ Delete/undelete methods can now update correct session")
            print("  ✓ Migration script backed up")
            print()
            print("PHASE 2 NOW COMPLETE!")
            print("  Test the complete functionality:")
            print("  1. Load a session - see computed number displayed")
            print("  2. Delete it - title changes, buttons update, number recomputes")
            print("  3. Undelete it - title restores, buttons update, number recomputes")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Could not find pattern.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase2_2_StoreDbSessionMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
