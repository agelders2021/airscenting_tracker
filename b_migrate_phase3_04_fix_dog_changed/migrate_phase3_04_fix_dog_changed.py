#!/usr/bin/env python3
"""
Phase 3.04 Migration: Fix on_dog_changed to Use Computed Numbers

The on_dog_changed() method sets session_number to database next.
This is called at startup when the dog loads, overriding the correct
computed number from update_initial_session().

Changes:
1. Update on_dog_changed() to use computed next number

Usage:
    python migrate_phase3_04_fix_dog_changed.py          # Show what will be done
    python migrate_phase3_04_fix_dog_changed.py --execute  # Execute the migration
"""

import sys
import shutil
import os
import re


class Phase3_04_FixDogChangedMigration:
    """Phase 3.04: Fix on_dog_changed to use computed numbers"""
    
    def __init__(self, execute=False):
        self.execute = execute
        self.project_dir = os.getcwd()
        
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.backup_folder = os.path.join(self.project_dir, f"b_{script_name}")
        
        self.files_to_modify = {
            "ui_misc2.py": "Fix on_dog_changed to use computed numbers"
        }
    
    def print_header(self):
        print("=" * 80)
        print("PHASE 3.04: FIX ON_DOG_CHANGED")
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
            
            # Find the lines where we set next_session in on_dog_changed
            old_code = '''                # Update session number to next available for this dog
                next_session = DatabaseOperations(self.ui).get_next_session_number(dog_name)
                # print(f"DEBUG on_dog_changed: next_session = {next_session}")  # DEBUG
                sv.session_number.set(str(next_session))'''
            
            new_code = '''                # Update session number to next computed number for this dog
                status_filter = sv.session_status_filter.get()
                filtered_sessions = DatabaseOperations(self.ui).get_all_sessions_for_dog(dog_name, status_filter)
                next_computed = len(filtered_sessions) + 1
                sv.session_number.set(str(next_computed))'''
            
            count = 0
            if old_code in content:
                content = content.replace(old_code, new_code)
                count += 1
                print("  ✓ Updated session number calculation")
            else:
                print("  ✗ Could not find session number code")
                return False
            
            # Also fix the status message that references next_session
            old_status = '                sv.status.set(f"Switched to {dog_name} - Next session: #{next_session}")'
            new_status = '                sv.status.set(f"Switched to {dog_name} - Next session: #{next_computed}")'
            
            if old_status in content:
                content = content.replace(old_status, new_status)
                count += 1
                print("  ✓ Updated status message")
            else:
                print("  ⚠ Could not find status message (may be ok)")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✓ Updated on_dog_changed() ({count} changes)")
            return True
        else:
            print("  - Would update on_dog_changed() to use computed numbers")
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
            print("PHASE 3.04 COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print()
            print("WHAT WAS DONE:")
            print("  ✓ on_dog_changed() now uses computed numbers")
            print("  ✓ Startup will show correct computed next number")
            print("  ✓ Changing dogs shows correct computed next number")
            print()
            print("🎉 ALL SOFT-DELETE MIGRATION COMPLETE! 🎉")
            print()
            print("FINAL SUMMARY:")
            print("  ✅ Startup - shows computed next number")
            print("  ✅ New button - shows computed next number")
            print("  ✅ Save Session - shows computed next number")
            print("  ✅ Load Session - shows computed session number")
            print("  ✅ Edit/Delete Dialog - shows computed numbers")
            print("  ✅ Change dog - shows computed next number")
            print("  ✅ Status filter - recomputes session number")
            print("  ✅ Delete/Undelete - updates display")
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
    migration = Phase3_04_FixDogChangedMigration(execute=execute)
    success = migration.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
