#!/usr/bin/env python3
"""
Phase 3.03 Migration: Fix Save Session Next Number

After saving and reloading, the code sets the next session number using the
database next number. It should use the computed next number instead.

Changes:
1. Replace database next number with computed next number after save

Usage:
    python migrate_phase3_03_fix_save_next.py          # Show what will be done
    python migrate_phase3_03_fix_save_next.py --execute  # Execute the migration
"""

import sys
import shutil
import os
import re


class Phase3_03_FixSaveNextMigration:
    """Phase 3.03: Fix save session to use computed next number"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_misc2.py": "Use computed next number after save"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 3.03: FIX SAVE SESSION NEXT NUMBER")
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
    
    def modify_ui_misc2(self):
        print("\n[1/1] Modifying ui_misc2.py...")
        
        filepath = os.path.join(self.project_dir, "ui_misc2.py")
        if not os.path.exists(filepath):
            print(f"  ✗ Error: {filepath} not found!")
            return False
        
        if self.execute:
            self.backup_file(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the line that sets next session to database number
            old_line = '        sv.session_number.set(str(DatabaseOperations(self).get_next_session_number()))'
            
            new_code = '''        # Set to computed next number based on filter
        status_filter = sv.session_status_filter.get()
        filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(dog_name, status_filter)
        next_computed = len(filtered_sessions) + 1
        sv.session_number.set(str(next_computed))'''
            
            if old_line in content:
                content = content.replace(old_line, new_code)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("  ✓ Replaced database next with computed next")
                return True
            else:
                print("  ✗ Could not find the line to replace")
                return False
        else:
            print("  - Would replace database next with computed next")
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
        
        if self.modify_ui_misc2():
            print("\n" + "=" * 80)
            print("PHASE 3.03 COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ After save, shows computed next number")
            print("  ✓ Based on current filter setting")
            print()
            print("ALL SOFT-DELETE MIGRATION NOW COMPLETE! 🎉")
            print()
            print("SUMMARY:")
            print("  ✅ Startup - computed numbers")
            print("  ✅ New - computed numbers")  
            print("  ✅ Save - computed numbers")
            print("  ✅ Load - computed numbers")
            print("  ✅ Dialog - computed numbers")
            print()
            print(f"Restore from: {self.backup_folder}/")
            return True
        else:
            print("\n" + "=" * 80)
            print("FAILED")
            print("=" * 80)
            return False


def main():
    execute = "--execute" in sys.argv
    migration = Phase3_03_FixSaveNextMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
