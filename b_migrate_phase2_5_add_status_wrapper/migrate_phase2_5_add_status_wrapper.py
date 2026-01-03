#!/usr/bin/env python3
"""
Phase 2.5 Migration: Add get_session_status Wrapper

This script adds the get_session_status() wrapper method to DatabaseOperations
class so it can call the method in DatabaseManager.

Changes:
1. Add get_session_status() wrapper to DatabaseOperations in ui_database.py

Usage:
    python migrate_phase2_5_add_status_wrapper.py          # Show what will be done
    python migrate_phase2_5_add_status_wrapper.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_5_AddStatusWrapperMigration:
    """Phase 2.5: Add get_session_status wrapper"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_database.py": "Add get_session_status wrapper to DatabaseOperations"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.5: ADD GET_SESSION_STATUS WRAPPER")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Add get_session_status() wrapper to DatabaseOperations:")
        print("   - Calls db_manager.get_session_status()")
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
    
    def modify_ui_database(self):
        """Add get_session_status wrapper to DatabaseOperations"""
        print("\n[1/1] Modifying ui_database.py...")
        
        filepath = os.path.join(self.project_dir, "ui_database.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add after update_session_status wrapper
            insertion_point = '''    def update_session_status(self, session_number, dog_name, new_status):
        """Update the status of a session (for delete/undelete)
        
        Args:
            session_number: Session number to update
            dog_name: Dog name
            new_status: 'active' or 'deleted'
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.db_manager.update_session_status(session_number, dog_name, new_status)
    
    def delete_sessions(self, session_numbers, dog_name):'''
            
            new_method = '''    def update_session_status(self, session_number, dog_name, new_status):
        """Update the status of a session (for delete/undelete)
        
        Args:
            session_number: Session number to update
            dog_name: Dog name
            new_status: 'active' or 'deleted'
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.db_manager.update_session_status(session_number, dog_name, new_status)
    
    def get_session_status(self, session_number, dog_name):
        """Get the status of a specific session
        
        Args:
            session_number: Session number (database value)
            dog_name: Dog name
        
        Returns:
            str: 'active', 'deleted', or None if not found
        """
        return self.db_manager.get_session_status(session_number, dog_name)
    
    def compute_session_number(self, dog_name, session_date, status_filter='active'):
        """Compute ordinal session number based on filter
        
        Args:
            dog_name: Dog name
            session_date: Session date
            status_filter: 'active', 'deleted', or 'both'
        
        Returns:
            int: Ordinal position in filtered list
        """
        return self.db_manager.compute_session_number(dog_name, session_date, status_filter)
    
    def delete_sessions(self, session_numbers, dog_name):'''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_method)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Added get_session_status() wrapper")
                print("  ✓ Added compute_session_number() wrapper")
                return True
            else:
                print("  ✗ Could not find insertion point")
                return False
        else:
            print("  - Would add get_session_status() wrapper")
            print("  - Would add compute_session_number() wrapper")
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
        results.append(self.modify_ui_database())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 2.5 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Added get_session_status() wrapper to DatabaseOperations")
            print("  ✓ Added compute_session_number() wrapper to DatabaseOperations")
            print("  ✓ Migration script backed up")
            print()
            print("NOW TRY AGAIN:")
            print("  Click View/Edit/Delete - should work now!")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Pattern not found.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase2_5_AddStatusWrapperMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
