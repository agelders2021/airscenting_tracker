#!/usr/bin/env python3
"""
Phase 1.91 Migration: Add update_session_status to DatabaseManager (CORRECTED)

This script adds update_session_status() to the DatabaseManager class
in ui_database.py (not database.py as Phase 1.90 tried).

Changes:
1. Add update_session_status() to DatabaseManager class in ui_database.py

Usage:
    python migrate_phase1_91_db_manager_update.py          # Show what will be done
    python migrate_phase1_91_db_manager_update.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase1_91_DbManagerUpdateMigration:
    """Phase 1.91: Add update_session_status to DatabaseManager class"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_database.py": "Add update_session_status to DatabaseManager class"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 1.91: ADD UPDATE_SESSION_STATUS TO DATABASE MANAGER")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Add to ui_database.py DatabaseManager class:")
        print("   - update_session_status(session_number, dog_name, new_status)")
        print("   - Executes UPDATE to set status field")
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
        """Add update_session_status to DatabaseManager in ui_database.py"""
        print("\n[1/1] Modifying ui_database.py...")
        
        filepath = os.path.join(self.project_dir, "ui_database.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add method in DatabaseManager class after delete_sessions
            # Look for the end of delete_sessions in DatabaseManager (not in DatabaseOperations wrapper)
            insertion_point = '''                print(f"Error getting sessions: {e}")
                return []
    
    def compute_session_number(self, dog_name, session_date, status_filter='active'):'''
            
            new_method = '''                print(f"Error getting sessions: {e}")
                return []
    
    def update_session_status(self, session_number, dog_name, new_status):
        """Update the status of a session (for delete/undelete)
        
        Args:
            session_number: Session number to update
            dog_name: Dog name
            new_status: 'active' or 'deleted'
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not dog_name or not dog_name.strip():
            return False
        
        dog_name = dog_name.strip()
        
        try:
            with get_connection() as conn:
                conn.execute(
                    text("""
                        UPDATE training_sessions 
                        SET status = :status, updated_at = CURRENT_TIMESTAMP
                        WHERE session_number = :session_number AND dog_name = :dog_name
                    """),
                    {"status": new_status, "session_number": session_number, "dog_name": dog_name}
                )
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error updating session status: {e}")
            return False
    
    def compute_session_number(self, dog_name, session_date, status_filter='active'):'''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_method)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Added update_session_status() to DatabaseManager class")
                return True
            else:
                print("  ✗ Could not find insertion point in DatabaseManager class")
                return False
        else:
            print("  - Would add update_session_status() to DatabaseManager class")
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
            print("PHASE 1.91 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Added update_session_status() to DatabaseManager in ui_database.py")
            print("  ✓ Migration script backed up")
            print()
            print("TEST IT:")
            print("  1. Load an existing session")
            print("  2. Click 'Delete' - session should be marked as deleted")
            print("  3. Click 'Undelete' - session should be restored to active")
            print("  4. Use status filter to verify changes")
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
    
    migration = Phase1_91_DbManagerUpdateMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
