#!/usr/bin/env python3
"""
Phase 2.3 Migration: Fix Computed Number Display (Correct Pattern)

This script fixes the issue where session numbers are still showing database
values instead of computed values. Uses the ACTUAL pattern in the file.

Changes:
1. Update load_session_by_number() to compute and display ordinal numbers
2. Update session frame title based on status
3. Enable/disable buttons based on status

Usage:
    python migrate_phase2_3_fix_computed_display.py          # Show what will be done
    python migrate_phase2_3_fix_computed_display.py --execute  # Execute the migration
"""

import sys
import shutil
import os
from datetime import datetime


class Phase2_3_FixComputedDisplayMigration:
    """Phase 2.3: Fix computed number display with correct pattern"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        # Create backup folder name from script name
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_navigation.py": "Update load_session_by_number to display computed numbers"
        }
    
    def print_header(self):
        """Print script header"""
        print("=" * 80)
        print("PHASE 2.3: FIX COMPUTED NUMBER DISPLAY")
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
        print("   - Compute ordinal session number based on current filter")
        print("   - Display computed number (not database number)")
        print("   - Update LabelFrame title based on status")
        print("   - Enable/disable Delete/Undelete buttons based on status")
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
        """Update load_session_by_number to display computed numbers"""
        print("\n[1/1] Modifying ui_navigation.py...")
        
        filepath = os.path.join(self.project_dir, "ui_navigation.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use the ACTUAL pattern that exists in the file
            old_pattern = '''            # Update subjects found dropdown based on loaded num_subjects
            form_mgmt = FormManagement(self.ui)
            form_mgmt.update_subjects_found()
            
            sv.status.set(f"Loaded session #{session_number}")'''
            
            new_pattern = '''            # Update subjects found dropdown based on loaded num_subjects
            form_mgmt = FormManagement(self.ui)
            form_mgmt.update_subjects_found()
            
            # Get session status and compute ordinal position
            session_status = db_ops.get_session_status(session_number, dog_name)
            status_filter = sv.session_status_filter.get()
            
            # Compute ordinal session number based on current filter
            computed_number = db_ops.compute_session_number(dog_name, session_dict["date"], status_filter)
            
            # Display computed number (not database session_number)
            sv.session_number.set(str(computed_number))
            
            # Update session frame title based on status
            self.update_session_frame_title(session_status)
            
            # Enable/disable delete/undelete buttons based on status
            if session_status == 'deleted':
                # Deleted session - disable Delete, enable Undelete
                if hasattr(self.ui, 'a_delete_undelete_frame'):
                    for child in self.ui.a_delete_undelete_frame.winfo_children():
                        button_text = child.cget('text')
                        if button_text == 'Delete':
                            child.config(state="disabled")
                        elif button_text == 'Undelete':
                            child.config(state="normal")
            else:
                # Active session - enable Delete, disable Undelete
                if hasattr(self.ui, 'a_delete_undelete_frame'):
                    for child in self.ui.a_delete_undelete_frame.winfo_children():
                        button_text = child.cget('text')
                        if button_text == 'Delete':
                            child.config(state="normal")
                        elif button_text == 'Undelete':
                            child.config(state="disabled")
            
            sv.status.set(f"Loaded session (computed #{computed_number})")'''
            
            if old_pattern in content:
                content = content.replace(old_pattern, new_pattern)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Updated load_session_by_number() to display computed numbers")
                return True
            else:
                print("  ✗ Could not find pattern in load_session_by_number()")
                print("  Pattern searched for:")
                print("    '# Update subjects found dropdown based on loaded num_subjects'")
                return False
        else:
            print("  - Would update load_session_by_number() to display computed numbers")
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
            print("PHASE 2.3 MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ load_session_by_number() now computes and displays ordinal numbers")
            print("  ✓ Session frame title updates based on status")
            print("  ✓ Delete/Undelete buttons enable/disable based on status")
            print("  ✓ Migration script backed up")
            print()
            print("TEST IT:")
            print("  1. Load a session - should see computed number")
            print("  2. Change filter - number should recompute")
            print("  3. Delete session - title changes to red/bold")
            print()
            print(f"RESTORE: If needed, copy files from {self.backup_folder}/")
            print()
            return True
        else:
            print("MIGRATION FAILED")
            print("=" * 80)
            print()
            print("Pattern not found in file.")
            print(f"Original files preserved in: {self.backup_folder}/")
            print()
            return False


def main():
    """Main entry point"""
    execute = "--execute" in sys.argv
    
    migration = Phase2_3_FixComputedDisplayMigration(execute=execute)
    success = migration.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
