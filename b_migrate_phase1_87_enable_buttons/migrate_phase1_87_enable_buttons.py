#!/usr/bin/env python3
"""
Phase 1.87 Migration: Enable Delete/Undelete Buttons When Loading Session

This script fixes the pattern to enable delete/undelete buttons when loading
an existing session in load_session_by_number().

Changes:
1. Add enable_delete_undelete_buttons() call in load_session_by_number()

Usage:
    python migrate_phase1_87_enable_buttons.py          # Show what will be done
    python migrate_phase1_87_enable_buttons.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase1_87_EnableButtonsMigration:
    """Phase 1.87: Enable buttons when loading session"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Enable delete/undelete buttons in load_session_by_number()"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 1.87: ENABLE BUTTONS WHEN LOADING SESSION")
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
        print("   - Call enable_delete_undelete_buttons() after loading session")
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
        """Update load_session_by_number to enable buttons"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the correct pattern - after updating subjects_found, before the else block
            old_pattern = '''            # Update subjects found dropdown based on loaded num_subjects
            form_mgmt = FormManagement(self.ui)
            form_mgmt.update_subjects_found()
            
            sv.status.set(f"Loaded session #{session_number}")
            
        else:'''
            
            new_pattern = '''            # Update subjects found dropdown based on loaded num_subjects
            form_mgmt = FormManagement(self.ui)
            form_mgmt.update_subjects_found()
            
            # Enable delete/undelete buttons (editing existing session)
            self.enable_delete_undelete_buttons()
            
            sv.status.set(f"Loaded session #{session_number}")
            
        else:'''
            
            if old_pattern in content:
                content = content.replace(old_pattern, new_pattern)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Updated load_session_by_number() to enable buttons")
                return True
            else:
                print("  ✗ Could not find load_session_by_number() pattern")
                return False
        else:
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
            print("PHASE 1.87 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ load_session_by_number() now enables delete/undelete buttons")
            print("  ✓ Migration script backed up")
            print()
            print("TEST IT:")
            print("  1. Load an existing session")
            print("  2. Delete/Undelete buttons should be enabled")
            print("  3. Click 'Delete' or 'Undelete'")
            print("  4. Click 'New' - buttons should be disabled")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Pattern could not be found.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase1_87_EnableButtonsMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
