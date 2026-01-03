#!/usr/bin/env python3
"""
Phase 2.62 Migration: Add on_status_filter_changed Method

This method was supposed to be added earlier but is missing. It handles
when the user clicks the status filter radio buttons.

Changes:
1. Add on_status_filter_changed() method to Navigation class

Usage:
    python migrate_phase2_62_add_filter_method.py          # Show what will be done
    python migrate_phase2_62_add_filter_method.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_62_AddFilterMethodMigration:
    """Phase 2.62: Add on_status_filter_changed method"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Add on_status_filter_changed method"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.62: ADD ON_STATUS_FILTER_CHANGED METHOD")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Add on_status_filter_changed() method to Navigation class:")
        print("   - Reloads current session if one is loaded")
        print("   - This recomputes session number based on new filter")
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
        """Add on_status_filter_changed method"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add method after delete_sessions method
            insertion_point = '''            form_mgmt = FormManagement(self.ui)
            form_mgmt.new_session()'''
            
            new_method = '''            form_mgmt = FormManagement(self.ui)
            form_mgmt.new_session()
    
    def on_status_filter_changed(self):
        """Called when status filter radio button changes"""
        from sv import sv
        status_filter = sv.session_status_filter.get()
        
        # If a session is currently loaded, reload it to recompute number
        if hasattr(self, 'current_db_session_number') and self.current_db_session_number:
            self.load_session_by_number(self.current_db_session_number)
        else:
            sv.status.set(f"Filter: {status_filter}")
            self.update_navigation_buttons()'''
            
            if insertion_point in content:
                content = content.replace(insertion_point, new_method)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Added on_status_filter_changed() method")
                return True
            else:
                print("  ✗ Could not find insertion point")
                return False
        else:
            print("  - Would add on_status_filter_changed() method")
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
            print("PHASE 2.62 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Added on_status_filter_changed() method")
            print("  ✓ Method reloads session when filter changes")
            print("  ✓ Session number recomputes based on new filter")
            print("  ✓ Migration script backed up")
            print()
            print("TEST IT:")
            print("  1. Load a session")
            print("  2. Change filter (Active/Deleted/Both)")
            print("  3. Session number should recompute")
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
    
    migration = Phase2_62_AddFilterMethodMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
