#!/usr/bin/env python3
"""
Phase 2.6 Migration: Add update_session_frame_title Method

This script adds the update_session_frame_title() method that updates
the Session Information LabelFrame title based on session status.

Changes:
1. Add update_session_frame_title() to Navigation class in ui_navigation.py

Usage:
    python migrate_phase2_6_add_frame_title.py          # Show what will be done
    python migrate_phase2_6_add_frame_title.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_6_AddFrameTitleMigration:
    """Phase 2.6: Add update_session_frame_title method"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Add update_session_frame_title method"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.6: ADD UPDATE_SESSION_FRAME_TITLE METHOD")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def print_changes(self):
        """Print what will be changed"""
        print("CHANGES TO BE MADE:")
        print()
        print("1. Add update_session_frame_title() to Navigation class:")
        print("   - Active: 'Session Information' (black, normal)")
        print("   - Deleted: 'Session Information *** MARKED DELETED ***' (red, bold)")
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
        """Add update_session_frame_title method"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add before enable_delete_undelete_buttons
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
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Added update_session_frame_title() method")
                return True
            else:
                print("  ✗ Could not find insertion point")
                return False
        else:
            print("  - Would add update_session_frame_title() method")
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
            print("PHASE 2.6 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ Added update_session_frame_title() method")
            print("  ✓ Migration script backed up")
            print()
            print("PHASE 2 SHOULD NOW BE COMPLETE!")
            print()
            print("TEST IT:")
            print("  1. Click View/Edit/Delete - should work now")
            print("  2. Load a session - see computed number")
            print("  3. Delete it - title turns red/bold")
            print("  4. Undelete it - title restores")
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
    
    migration = Phase2_6_AddFrameTitleMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
