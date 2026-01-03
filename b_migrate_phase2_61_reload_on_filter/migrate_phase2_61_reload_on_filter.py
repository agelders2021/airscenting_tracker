#!/usr/bin/env python3
"""
Phase 2.07 Migration: Reload Session When Filter Changes

When the user changes the status filter radio button, reload the current
session so the computed number updates to reflect the new filter.

Changes:
1. Update on_status_filter_changed() to reload current session
2. This causes the number to recompute based on new filter

Usage:
    python migrate_phase2_07_reload_on_filter.py          # Show what will be done
    python migrate_phase2_07_reload_on_filter.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_07_ReloadOnFilterMigration:
    """Phase 2.07: Reload session when filter changes"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Update on_status_filter_changed to reload session"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.07: RELOAD SESSION WHEN FILTER CHANGES")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Update on_status_filter_changed() in ui_navigation.py:")
        print("   - If a session is currently loaded, reload it")
        print("   - This recomputes the session number based on new filter")
        print("   - Session number will change to reflect position in filtered list")
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
        """Update on_status_filter_changed to reload session"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find and replace on_status_filter_changed
            old_method = '''    def on_status_filter_changed(self):
        """Called when status filter radio button changes"""
        from sv import sv
        status_filter = sv.session_status_filter.get()
        sv.status.set(f"Filter: {status_filter}")
        self.update_navigation_buttons()'''
            
            new_method = '''    def on_status_filter_changed(self):
        """Called when status filter radio button changes"""
        from sv import sv
        status_filter = sv.session_status_filter.get()
        
        # If a session is currently loaded, reload it to recompute number
        if hasattr(self, 'current_db_session_number') and self.current_db_session_number:
            self.load_session_by_number(self.current_db_session_number)
        else:
            sv.status.set(f"Filter: {status_filter}")
            self.update_navigation_buttons()'''
            
            if old_method in content:
                content = content.replace(old_method, new_method)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Updated on_status_filter_changed() to reload session")
                return True
            else:
                print("  ✗ Could not find on_status_filter_changed() method")
                return False
        else:
            print("  - Would update on_status_filter_changed() to reload session")
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
            print("PHASE 2.07 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ on_status_filter_changed() now reloads current session")
            print("  ✓ Session number recomputes when filter changes")
            print("  ✓ Migration script backed up")
            print()
            print("TEST IT:")
            print("  1. Load a session - note the number")
            print("  2. Change filter (Active/Deleted/Both)")
            print("  3. Number should recompute based on position in new filtered list")
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
    
    migration = Phase2_07_ReloadOnFilterMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
