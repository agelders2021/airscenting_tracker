#!/usr/bin/env python3
"""
Phase 2.70 Migration: Reset UI When Clicking New (Correct Pattern)

When user clicks "New" button:
1. Reset LabelFrame title to "Session Information" (normal, black)
2. Set filter radio button back to "active"

Changes:
1. Update new_session() in ui_form_management.py to reset UI state

Usage:
    python migrate_phase2_70_reset_new_fixed.py          # Show what will be done
    python migrate_phase2_70_reset_new_fixed.py --execute  # Execute the migration
"""

import sys
import shutil
import os


class Phase2_70_ResetNewMigration:
    """Phase 2.70: Reset UI state when clicking New (correct pattern)"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_form_management.py": "Reset LabelFrame title and filter when clicking New"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 2.70: RESET UI WHEN CLICKING NEW (FIXED)")
        print("=" * 80)
        print()
        print(f"Working directory: {self.project_dir}")
        print(f"Backup folder: {self.backup_folder}")
        print()
    
    def create_backup_folder(self):
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)
    
    def backup_file(self, filepath):
        self.create_backup_folder()
        filename = os.path.basename(filepath)
        backup_path = os.path.join(self.backup_folder, filename)
        shutil.copy2(filepath, backup_path)
        print(f"  ✓ Backed up: {filename}")
    
    def backup_script(self):
        self.create_backup_folder()
        script_path = os.path.abspath(sys.argv[0])
        script_name = os.path.basename(script_path)
        backup_path = os.path.join(self.backup_folder, script_name)
        shutil.copy2(script_path, backup_path)
        print(f"  ✓ Backed up script")
    
    def modify_ui_form_management(self):
        print("\n[1/1] Modifying ui_form_management.py...")
        
        filepath = os.path.join(self.project_dir, "ui_form_management.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'rb') as f:
                content = f.read().decode('utf-8')
            
            # Find the actual pattern that exists in the file
            old_code = '''        sv.status.set(f"New session #{next_session}")
        
        # Update navigation buttons
        nav = Navigation(self.ui)
        nav.update_navigation_buttons()'''
            
            new_code = '''        sv.status.set(f"New session #{next_session}")
        
        # Reset UI to active state
        sv.session_status_filter.set('active')  # Reset filter to active
        
        # Reset LabelFrame title to normal (not deleted)
        if hasattr(self.ui, 'a_session_frame'):
            self.ui.a_session_frame.config(
                text="Session Information",
                foreground="black",
                font=("TkDefaultFont", 9)
            )
        
        # Update navigation buttons
        nav = Navigation(self.ui)
        nav.update_navigation_buttons()'''
            
            if old_code in content:
                content = content.replace(old_code, new_code)
                
                with open(filepath, 'wb') as f:
                    f.write(content.encode('utf-8'))
                
                print("  ✓ Updated new_session() to reset UI state")
                return True
            else:
                print("  ✗ Could not find the code to replace")
                return False
        else:
            print("  - Would update new_session() to reset UI state")
            return True
    
    def run(self):
        self.print_header()
        
        if not self.execute:
            print("DRY RUN")
            print()
            print("To execute: python", os.path.basename(sys.argv[0]), "--execute")
            return True
        
        print("EXECUTING")
        print()
        
        response = input("Proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("\nCancelled.")
            return False
        
        print()
        self.backup_script()
        print()
        
        if self.modify_ui_form_management():
            print("\n" + "=" * 80)
            print("PHASE 2.70 COMPLETED")
            print("=" * 80)
            print("\n✓ Clicking 'New' now resets filter to 'active'")
            print("✓ LabelFrame title resets to normal (black)")
            print(f"\nRestore from: {self.backup_folder}/")
            return True
        else:
            print("\n" + "=" * 80)
            print("FAILED")
            print("=" * 80)
            return False


def main():
    execute = "--execute" in sys.argv
    migration = Phase2_70_ResetNewMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
