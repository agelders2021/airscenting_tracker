#!/usr/bin/env python3
"""
Phase 1.85 Migration: Fix new_session() to Disable Delete/Undelete Buttons

This script fixes the pattern that failed in Phase 1.80 for disabling
delete/undelete buttons when creating a new session.

Also adds feature: Script copies itself to backup directory for reconstruction.

Changes:
1. Update new_session() in ui_form_management.py to disable delete/undelete buttons

Usage:
    python migrate_phase1_85_fix_new_session.py          # Show what will be done
    python migrate_phase1_85_fix_new_session.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase1_85_FixNewSessionMigration:
    """Phase 1.85: Fix new_session() pattern"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_form_management.py": "Disable delete/undelete buttons in new_session()"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 1.85: FIX NEW_SESSION() BUTTON DISABLE")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Update new_session() in ui_form_management.py:")
        print("   - Add call to nav.disable_delete_undelete_buttons()")
        print("   - Buttons will be disabled when creating new session")
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
    
    def modify_ui_form_management(self):
        """Update new_session to disable buttons"""
        print("\n[1/1] Modifying ui_form_management.py...")
        
        filepath = os.path.join(self.project_dir, "ui_form_management.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find new_session method and add disable call
            old_new = '''        sv.status.set(f"New session #{next_session}")
        
        # Update navigation buttons
        nav = Navigation(self.ui)
        nav.update_navigation_buttons()'''
            
            new_new = '''        sv.status.set(f"New session #{next_session}")
        
        # Disable delete/undelete buttons (creating new session)
        nav = Navigation(self.ui)
        nav.disable_delete_undelete_buttons()
        
        # Update navigation buttons
        nav.update_navigation_buttons()'''
            
            if old_new in content:
                content = content.replace(old_new, new_new)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Updated new_session() to disable delete/undelete buttons")
                return True
            else:
                print("  ✗ Could not find new_session() pattern")
                return False
        else:
            print("  - Would update new_session() to disable delete/undelete buttons")
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
        
        # NEW: Backup the migration script itself first
        self.backup_script()
        print()
        
        results = []
        results.append(self.modify_ui_form_management())
        
        print("\n" + "=" * 80)
        if all(results):
            print("PHASE 1.85 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ new_session() now disables delete/undelete buttons")
            print("  ✓ Migration script backed up to restore folder")
            print()
            print("TEST IT:")
            print("  1. Load an existing session - buttons should be enabled")
            print("  2. Click 'New' - buttons should become disabled")
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
    
    migration = Phase1_85_FixNewSessionMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
